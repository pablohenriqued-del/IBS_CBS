"""Endpoints públicos:

- Download de artefatos de marketing (vídeo, carrossel, trailer 20s).
- Contato inline (captura de leads sem depender de LinkedIn DM).
- Estatísticas do modo demo (prova social para o footer).
- Rate limiter em memória para o modo demo (10 chamadas/hora por IP).
"""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .audit_ledger import append_event
from .auth import require_role
from .db import get_db

router = APIRouter(prefix="/api/public")


_ARTIFACTS = {
    "video": {
        "path": "/app/video/FiscalCore-LinkedIn.mp4",
        "media": "video/mp4",
        "filename": "FiscalCore-LinkedIn.mp4",
    },
    "trailer": {
        "path": "/app/video/FiscalCore-Reels-20s.mp4",
        "media": "video/mp4",
        "filename": "FiscalCore-Reels-20s.mp4",
    },
    "carrossel": {
        "path": "/app/FiscalCore-LinkedIn-Carousel.pdf",
        "media": "application/pdf",
        "filename": "FiscalCore-LinkedIn-Carousel.pdf",
    },
}


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


@router.get("/download/{artifact_id}")
async def baixar_artefato(artifact_id: str):
    art = _ARTIFACTS.get(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail={"erro": "artefato_nao_encontrado"})
    if not os.path.exists(art["path"]):
        raise HTTPException(status_code=404, detail={"erro": "arquivo_ainda_nao_gerado"})
    return FileResponse(
        art["path"],
        media_type=art["media"],
        filename=art["filename"],
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": f'attachment; filename="{art["filename"]}"',
        },
    )


@router.get("/artefatos")
async def listar_artefatos():
    itens = []
    for aid, meta in _ARTIFACTS.items():
        exists = os.path.exists(meta["path"])
        size = os.path.getsize(meta["path"]) if exists else 0
        itens.append({
            "id": aid,
            "filename": meta["filename"],
            "media_type": meta["media"],
            "disponivel": exists,
            "tamanho_bytes": size,
            "download_url": f"/api/public/download/{aid}",
        })
    return {"artefatos": itens}


# ---------------------------------------------------------------------------
# Contato inline
# ---------------------------------------------------------------------------


class ContatoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    empresa: Optional[str] = Field(default=None, max_length=120)
    mensagem: str = Field(min_length=4, max_length=1200)
    origem: Optional[str] = Field(default="sobre", max_length=40)


@router.post("/contato")
async def registrar_contato(req: ContatoRequest, request: Request):
    """Recebe um lead do formulário público. Grava em Mongo e no ledger auditável."""
    ip = _get_ip(request)
    ua = request.headers.get("user-agent", "")[:200]

    db = get_db()
    doc = {
        "nome": req.nome.strip(),
        "email": str(req.email).lower(),
        "empresa": (req.empresa or "").strip() or None,
        "mensagem": req.mensagem.strip(),
        "origem": req.origem,
        "ip": ip,
        "user_agent": ua,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "novo",
    }
    result = await db.contatos.insert_one(doc)

    await append_event(
        action="contato.novo",
        payload={
            "email": doc["email"],
            "nome": doc["nome"],
            "empresa": doc["empresa"],
            "origem": doc["origem"],
        },
        actor={"id": "anonymous", "email": doc["email"], "role": "visitante"},
    )

    return {
        "ok": True,
        "id": str(result.inserted_id),
        "mensagem": "Recebido. Vou responder por e-mail nas próximas 48h.",
    }


@router.get("/contato/lista")
async def listar_contatos(
    limit: int = 100,
    _user: dict = Depends(require_role("admin")),
):
    """Admin-only: lista os contatos recebidos, mais recentes primeiro."""
    db = get_db()
    cursor = db.contatos.find({}, {"ip": 0, "user_agent": 0}).sort("created_at", -1).limit(limit)
    itens: List[dict] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        itens.append(doc)
    return {"total": len(itens), "contatos": itens}


# ---------------------------------------------------------------------------
# Estatísticas (prova social)
# ---------------------------------------------------------------------------


@router.get("/stats")
async def stats_publicas():
    """Contadores públicos para prova social no footer / landing."""
    db = get_db()
    total_calc = await db.auditoria_ledger.count_documents({"action": "calcular"})
    total_demo = await db.auditoria_ledger.count_documents(
        {"action": "calcular", "actor.role": "demo"}
    )
    total_docs = await db.documentos.count_documents({})
    ultimo_demo_ev = await db.auditoria_ledger.find_one(
        {"action": "calcular", "actor.role": "demo"},
        sort=[("seq", -1)],
    )
    return {
        "calculos_totais": total_calc,
        "calculos_demo": total_demo,
        "documentos_importados": total_docs,
        "ultimo_demo_iso": (ultimo_demo_ev or {}).get("ts"),
    }


# ---------------------------------------------------------------------------
# Rate limiter em memória (10 chamadas/hora por IP no modo demo)
# ---------------------------------------------------------------------------


DEMO_MAX_POR_HORA = 10
_DEMO_WINDOW_SECS = 3600
_demo_calls: Dict[str, Deque[float]] = defaultdict(deque)


def _get_ip(request: Request) -> str:
    """Extrai IP considerando proxies/ingress. Cai para client.host."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    return (request.client.host if request.client else "0.0.0.0")


def demo_rate_check(request: Request) -> Dict[str, int]:
    """Aplica sliding window de {DEMO_MAX_POR_HORA} calls / {DEMO_WINDOW_SECS}s.

    Retorna dict com {remaining, retry_after}. Lança 429 se estourou.
    """
    ip = _get_ip(request)
    now = time.time()
    q = _demo_calls[ip]
    # descarta timestamps fora da janela
    while q and q[0] < now - _DEMO_WINDOW_SECS:
        q.popleft()
    if len(q) >= DEMO_MAX_POR_HORA:
        retry_after = int(q[0] + _DEMO_WINDOW_SECS - now)
        raise HTTPException(
            status_code=429,
            detail={
                "erro": "rate_limit_demo",
                "mensagem": (
                    f"Modo demo limitado a {DEMO_MAX_POR_HORA} cálculos por hora "
                    f"por IP. Tente novamente em {max(1, retry_after)}s ou entre "
                    f"com credenciais fiscal/admin."
                ),
                "retryAfterSeconds": max(1, retry_after),
            },
            headers={"Retry-After": str(max(1, retry_after))},
        )
    q.append(now)
    return {
        "remaining": DEMO_MAX_POR_HORA - len(q),
        "reset_in": _DEMO_WINDOW_SECS,
    }


def demo_reset_all():
    """Uso para testes."""
    _demo_calls.clear()
