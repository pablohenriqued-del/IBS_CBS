"""Rotas de ingestão de NF-e, listagem de documentos, apuração e audit ledger."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import Response

from .audit_ledger import append_event, listar_eventos, verificar_integridade
from .auth import get_current_user, require_role
from .db import get_db
from .nfe_parser import NFeParseError
from .servicos import (
    DocumentoJaImportado,
    SemRulesetVigente,
    apurar_periodo,
    importar_documento,
)

router = APIRouter(prefix="/api/v1")

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


# ---------------------- Amostras de NF-e ----------------------

_SAMPLES_META = [
    {
        "arquivo": "01-cadeira-integral.xml",
        "titulo": "Cadeira · tributação integral",
        "resumo": "1 item · R$ 1.000 · CBS 88 + IBS 177 = R$ 265",
        "direcao": "saida",
        "dataOperacao": "2026-08-26",
        "ruleset": "regime pleno",
    },
    {
        "arquivo": "02-medicamento-reducao60.xml",
        "titulo": "Medicamento · redução de 60%",
        "resumo": "1 item · R$ 500 · CBS 17,60 + IBS 35,40 = R$ 53",
        "direcao": "saida",
        "dataOperacao": "2026-08-26",
        "ruleset": "regime pleno",
    },
    {
        "arquivo": "03-bebida-imposto-seletivo.xml",
        "titulo": "Bebida · com Imposto Seletivo",
        "resumo": "1 item · R$ 200 + IS 10% · IS entra na base → R$ 78,30",
        "direcao": "saida",
        "dataOperacao": "2026-08-26",
        "ruleset": "regime pleno",
    },
    {
        "arquivo": "04-nota-completa-3-itens.xml",
        "titulo": "Nota completa · 3 itens (caso-ouro)",
        "resumo": "Cadeira + medicamento + bebida · tributos R$ 376,30",
        "direcao": "saida",
        "dataOperacao": "2026-08-26",
        "ruleset": "regime pleno",
    },
    {
        "arquivo": "05-entrada-fornecedor.xml",
        "titulo": "Entrada · papel + canetas (crédito)",
        "resumo": "2 itens · R$ 1.000 · gera crédito para apuração",
        "direcao": "entrada",
        "dataOperacao": "2026-08-20",
        "ruleset": "regime pleno",
    },
    {
        "arquivo": "06-fase-teste-2026.xml",
        "titulo": "Fase-teste 2026 · CBS 0,9% + IBS 0,1%",
        "resumo": "R$ 1.000 emitido em 15/03/2026 · R$ 10 em tributos",
        "direcao": "saida",
        "dataOperacao": "2026-03-15",
        "ruleset": "fase-teste",
    },
]


@router.get("/samples")
async def listar_amostras(_user: dict = Depends(get_current_user)):
    return {"amostras": _SAMPLES_META, "total": len(_SAMPLES_META)}


@router.get("/samples/{nome}")
async def baixar_amostra(nome: str, _user: dict = Depends(get_current_user)):
    # Sanitiza nome (não permite path traversal)
    if "/" in nome or ".." in nome or not nome.endswith(".xml"):
        raise HTTPException(status_code=400, detail="nome de arquivo inválido")
    caminho = SAMPLES_DIR / nome
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="amostra não encontrada")
    conteudo = caminho.read_bytes()
    return Response(
        content=conteudo,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ---------------------- Documentos ----------------------


@router.post("/documentos/importar")
async def importar(
    arquivo: UploadFile = File(...),
    direcao: str = Form(..., pattern="^(entrada|saida)$"),
    origem: Optional[str] = Form(None),
    user: dict = Depends(require_role("fiscal", "admin")),
):
    conteudo = await arquivo.read()
    if len(conteudo) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=413, detail="arquivo excede 5 MB")
    try:
        doc = await importar_documento(
            conteudo,
            direcao,
            actor={"id": user["id"], "email": user["email"], "role": user["role"]},
        )
    except NFeParseError as e:
        raise HTTPException(status_code=422, detail=f"XML inválido: {e}")
    except DocumentoJaImportado as e:
        raise HTTPException(
            status_code=409,
            detail={"erro": "documento_ja_importado", "chaveAcesso": e.chave, "id": e.doc_id},
        )
    except SemRulesetVigente as e:
        raise HTTPException(
            status_code=422,
            detail={"erro": "sem_ruleset_vigente", "dataOperacao": e.data},
        )

    ledger_payload = {
        "chaveAcesso": doc["chaveAcesso"],
        "direcao": doc["direcao"],
        "dataOperacao": doc["dataOperacao"],
        "cbs": doc["totais"]["cbs"],
        "ibs": doc["totais"]["ibs"],
        "impostoSeletivo": doc["totais"]["impostoSeletivo"],
        "rulesetId": doc["rulesetId"],
        "arquivo": arquivo.filename,
    }
    if origem:
        ledger_payload["origem"] = origem
    await append_event(
        action="documento.importado",
        payload=ledger_payload,
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )
    return doc


@router.get("/documentos")
async def listar_documentos(
    direcao: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    q = {}
    if direcao in ("entrada", "saida"):
        q["direcao"] = direcao
    cursor = db.documentos.find(q, {"itens": 0}).sort("dataOperacao", -1).limit(limit)
    docs = []
    async for d in cursor:
        d["id"] = str(d.pop("_id"))
        docs.append(d)
    return {"documentos": docs, "total": len(docs)}


@router.get("/documentos/{doc_id}")
async def obter_documento(doc_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="id inválido")
    d = await db.documentos.find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="documento não encontrado")
    d["id"] = str(d.pop("_id"))
    return d


# ---------------------- Apuração ----------------------


@router.post("/apuracao/periodo")
async def apuracao_periodo(
    payload: dict,
    user: dict = Depends(get_current_user),
):
    try:
        inicio = date.fromisoformat(payload["dataInicio"])
        fim = date.fromisoformat(payload["dataFim"])
    except Exception:
        raise HTTPException(status_code=422, detail="dataInicio/dataFim inválidos (use YYYY-MM-DD)")
    if inicio > fim:
        raise HTTPException(status_code=422, detail="dataInicio > dataFim")

    resultado = await apurar_periodo(inicio, fim)
    await append_event(
        action="apuracao.consultada",
        payload={"periodo": resultado["periodo"], "totalDocs": resultado["totalDocumentos"]},
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )
    return resultado


# ---------------------- Audit ledger ----------------------


@router.get("/auditoria/ledger")
async def ledger(
    limit: int = 200,
    _user: dict = Depends(require_role("auditoria", "admin")),
):
    eventos = await listar_eventos(limit=limit)
    return {"eventos": eventos, "total": len(eventos)}


@router.get("/auditoria/verificar")
async def verificar(_user: dict = Depends(require_role("auditoria", "admin"))):
    return await verificar_integridade()
