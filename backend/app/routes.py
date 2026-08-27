"""Rotas HTTP do FiscalCore Motor — cálculo IBS/CBS."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

from .audit_ledger import append_event
from .auth import get_current_user, require_role
from .db import (
    carregar_rulesets,
    get_auditoria,
    gravar_auditoria,
)
from .models import CalcularRequest, CalcularResponse, ErroDetalhe, ErroResponse
from .motor import CClassTribDesconhecido, calcular
from .rulesets import compute_ruleset_hash, resolver_ruleset

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "servico": "fiscalcore-motor"}


@router.get("/rulesets")
async def listar_rulesets() -> Dict[str, Any]:
    rulesets = await carregar_rulesets()
    return {"rulesets": rulesets, "total": len(rulesets)}


@router.get("/auditoria/calculos/{auditoria_id}")
async def obter_auditoria(
    auditoria_id: str,
    _user: dict = Depends(require_role("auditoria", "admin", "fiscal")),
) -> Dict[str, Any]:
    doc = await get_auditoria(auditoria_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"erro": "auditoria_nao_encontrada"})
    return doc


@router.post("/calcular", response_model=CalcularResponse, responses={422: {"model": ErroResponse}})
async def calcular_endpoint(
    req: CalcularRequest,
    request: Request,
    user: dict = Depends(require_role("fiscal", "admin")),
) -> CalcularResponse:
    rulesets = await carregar_rulesets()
    ruleset = resolver_ruleset(rulesets, req.dataOperacao)
    if ruleset is None:
        raise HTTPException(
            status_code=422,
            detail=ErroResponse(
                erro="validacao",
                detalhes=[
                    ErroDetalhe(
                        campo="dataOperacao",
                        codigo="sem_ruleset_vigente",
                        mensagem=f"Nenhum ruleset vigente para a data {req.dataOperacao.isoformat()}.",
                    )
                ],
            ).model_dump(),
        )

    ruleset_hash = compute_ruleset_hash(ruleset)

    try:
        itens_out, totais, avisos = calcular(req, ruleset)
    except CClassTribDesconhecido as e:
        raise HTTPException(
            status_code=422,
            detail=ErroResponse(
                erro="validacao",
                detalhes=[
                    ErroDetalhe(
                        campo=f"itens[{e.numero_item - 1}].cClassTrib",
                        codigo="cclasstrib_desconhecido",
                        mensagem=f"Código {e.codigo} não encontrado no ruleset {e.ruleset_id}.",
                    )
                ],
            ).model_dump(),
        )

    motor_versao = os.environ.get("MOTOR_VERSAO", "dev")
    calculado_em = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp_sem_auditoria = {
        "referencia": req.referencia,
        "rulesetId": ruleset["id"],
        "rulesetHash": ruleset_hash,
        "motorVersao": motor_versao,
        "calculadoEm": calculado_em,
        "moeda": "BRL",
        "arredondamento": "2 casas, meio-para-cima",
        "itens": [i.model_dump() for i in itens_out],
        "totais": totais.model_dump(),
        "avisos": avisos,
    }

    registro_auditoria = {
        "criadoEm": calculado_em,
        "input": req.model_dump(mode="json"),
        "rulesetId": ruleset["id"],
        "rulesetHash": ruleset_hash,
        "motorVersao": motor_versao,
        "idempotencyKey": request.headers.get("Idempotency-Key"),
        "output": resp_sem_auditoria,
        "actor": {"id": user["id"], "email": user["email"], "role": user["role"]},
    }
    auditoria_id = await gravar_auditoria(registro_auditoria)

    await append_event(
        action="calcular",
        payload={
            "referencia": req.referencia,
            "rulesetId": ruleset["id"],
            "tributosTotais": totais.tributosTotais,
            "auditoriaId": auditoria_id,
        },
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )

    return CalcularResponse(**resp_sem_auditoria, auditoriaId=auditoria_id)
