"""Serviços de documentos e apuração por período.

- `importar_documento`: parse XML, resolve ruleset pela dataOperacao, roda o
  motor de cálculo, persiste (idempotente por chaveAcesso).
- `apurar_periodo`: soma débitos (saídas) e créditos (entradas) no intervalo.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Tuple

from .db import get_db
from .models import (
    Acrescimos,
    CalcularRequest,
    Destinatario,
    Estabelecimento,
    ImpostoSeletivoIn,
    Item,
    Operacao,
)
from .motor import CClassTribDesconhecido, calcular
from .nfe_parser import parse_nfe
from .rulesets import compute_ruleset_hash, resolver_ruleset

Direcao = Literal["entrada", "saida"]


class DocumentoJaImportado(Exception):
    def __init__(self, chave: str, doc_id: str):
        self.chave = chave
        self.doc_id = doc_id
        super().__init__(f"documento com chave {chave} já importado (id={doc_id})")


class SemRulesetVigente(Exception):
    def __init__(self, data: str):
        self.data = data
        super().__init__(f"nenhum ruleset vigente em {data}")


# --------------------------------------------------------------------------
# Construção do request do motor a partir do parse
# --------------------------------------------------------------------------


def _fallback_cclasstrib(item: Dict[str, Any]) -> str:
    """Se o XML não informar cClassTrib, assumimos tributação integral (000001).
    O motor ainda vai falhar 422 se essa hipótese for inválida — mas é o
    default fiscalmente mais conservador (não subestima tributos)."""
    return item.get("cClassTrib") or "000001"


def build_calcular_request(
    parsed: Dict[str, Any],
    direcao: Direcao,
    referencia: str,
) -> CalcularRequest:
    itens_req = []
    for i, it in enumerate(parsed["itens"], start=1):
        acrescimos = None
        is_in = None
        if it.get("impostoSeletivo"):
            is_in = ImpostoSeletivoIn(
                aliquota=str(it["impostoSeletivo"]["aliquota"]),
                cst=it["impostoSeletivo"].get("cst"),
            )
        itens_req.append(
            Item(
                numero=it.get("numero") or i,
                descricao=it.get("xProd"),
                ncm=it.get("ncm"),
                cClassTrib=_fallback_cclasstrib(it),
                cst=it.get("cst"),
                quantidade=str(it.get("quantidade") or "1"),
                valorUnitario=str(it.get("valorUnitario") or "0"),
                valorItem=str(it.get("valorItem") or "0"),
                impostoSeletivo=is_in,
                acrescimos=acrescimos,
            )
        )

    # Para o motor, "estabelecimento" é sempre o dono da operação (quem apura).
    # Em entrada, ele é o destinatário; em saída, é o emitente. Guardamos ambos
    # no documento persistido.
    if direcao == "saida":
        est_cnpj = parsed["emitente"].get("cnpj") or "00000000000000"
        est_uf = parsed["emitente"].get("uf") or "SP"
        dest_uf = parsed["destinatario"].get("uf") or est_uf
        tipo_op = "venda"
    else:
        est_cnpj = parsed["destinatario"].get("cnpj") or "00000000000000"
        est_uf = parsed["destinatario"].get("uf") or "SP"
        dest_uf = parsed["emitente"].get("uf") or est_uf
        tipo_op = "venda"

    return CalcularRequest(
        referencia=referencia,
        dataOperacao=date.fromisoformat(parsed["dataOperacao"]),
        modo="producao",
        estabelecimento=Estabelecimento(
            cnpj=est_cnpj, uf=est_uf, municipioIBGE="0000000", regime="regular"
        ),
        destinatario=Destinatario(
            uf=dest_uf, municipioIBGE="0000000", consumidorFinal=True, contribuinte=False
        ),
        operacao=Operacao(tipo=tipo_op),
        itens=itens_req,
    )


# --------------------------------------------------------------------------
# Ingestão
# --------------------------------------------------------------------------


async def importar_documento(
    xml_bytes: bytes, direcao: Direcao, actor: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    db = get_db()
    parsed = parse_nfe(xml_bytes)

    # Idempotência por chave de acesso
    existente = await db.documentos.find_one({"chaveAcesso": parsed["chaveAcesso"]})
    if existente:
        raise DocumentoJaImportado(parsed["chaveAcesso"], str(existente["_id"]))

    # Resolver ruleset por dataOperacao
    from .db import carregar_rulesets

    rulesets = await carregar_rulesets()
    ruleset = resolver_ruleset(rulesets, date.fromisoformat(parsed["dataOperacao"]))
    if ruleset is None:
        raise SemRulesetVigente(parsed["dataOperacao"])
    ruleset_hash = compute_ruleset_hash(ruleset)

    # Rodar motor
    referencia = f"nfe:{parsed['chaveAcesso']}"
    req = build_calcular_request(parsed, direcao, referencia)
    itens_out, totais, avisos = calcular(req, ruleset)

    doc = {
        "chaveAcesso": parsed["chaveAcesso"],
        "direcao": direcao,
        "dataEmissao": parsed["dataEmissao"],
        "dataOperacao": parsed["dataOperacao"],
        "natOp": parsed.get("natOp"),
        "emitente": parsed["emitente"],
        "destinatario": parsed["destinatario"],
        "itens": [i.model_dump() for i in itens_out],
        "totais": totais.model_dump(),
        "avisos": avisos,
        "rulesetId": ruleset["id"],
        "rulesetHash": ruleset_hash,
        "referencia": referencia,
        "importadoEm": datetime.utcnow().isoformat(),
        "importadoPor": actor,
    }
    result = await db.documentos.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


# --------------------------------------------------------------------------
# Apuração por período
# --------------------------------------------------------------------------


async def apurar_periodo(
    data_inicio: date, data_fim: date, direcao_filter: Optional[Direcao] = None
) -> Dict[str, Any]:
    db = get_db()
    q: Dict[str, Any] = {
        "dataOperacao": {"$gte": data_inicio.isoformat(), "$lte": data_fim.isoformat()},
    }
    if direcao_filter:
        q["direcao"] = direcao_filter

    debitos = {
        "cbs": Decimal("0"),
        "ibs": Decimal("0"),
        "ibsUF": Decimal("0"),
        "ibsMunicipio": Decimal("0"),
        "impostoSeletivo": Decimal("0"),
        "base": Decimal("0"),
        "documentos": 0,
    }
    creditos = {k: Decimal("0") for k in debitos}

    documentos_resumo = []
    cursor = db.documentos.find(q).sort("dataOperacao", 1)
    async for d in cursor:
        t = d["totais"]
        bucket = debitos if d["direcao"] == "saida" else creditos
        bucket["base"] += Decimal(t["baseTotal"])
        bucket["cbs"] += Decimal(t["cbs"])
        bucket["ibsUF"] += Decimal(t["ibsUF"])
        bucket["ibsMunicipio"] += Decimal(t["ibsMunicipio"])
        bucket["ibs"] += Decimal(t["ibs"])
        bucket["impostoSeletivo"] += Decimal(t["impostoSeletivo"])
        bucket["documentos"] += 1
        documentos_resumo.append(
            {
                "id": str(d["_id"]),
                "chaveAcesso": d["chaveAcesso"],
                "direcao": d["direcao"],
                "dataOperacao": d["dataOperacao"],
                "emitente": d["emitente"].get("xNome"),
                "destinatario": d["destinatario"].get("xNome"),
                "cbs": t["cbs"],
                "ibs": t["ibs"],
                "impostoSeletivo": t["impostoSeletivo"],
                "tributosTotais": t["tributosTotais"],
            }
        )

    apurado = {
        "cbs": debitos["cbs"] - creditos["cbs"],
        "ibs": debitos["ibs"] - creditos["ibs"],
        "ibsUF": debitos["ibsUF"] - creditos["ibsUF"],
        "ibsMunicipio": debitos["ibsMunicipio"] - creditos["ibsMunicipio"],
    }
    apurado["total"] = apurado["cbs"] + apurado["ibs"]

    def _fmt(bucket: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for k, v in bucket.items():
            out[k] = int(v) if k == "documentos" else f"{v:.2f}"
        return out

    return {
        "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
        "debitos": _fmt(debitos),
        "creditos": _fmt(creditos),
        "apurado": {k: f"{v:.2f}" for k, v in apurado.items()},
        "documentos": documentos_resumo,
        "totalDocumentos": len(documentos_resumo),
    }
