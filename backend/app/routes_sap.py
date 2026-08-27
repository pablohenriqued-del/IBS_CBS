"""SAP S/4HANA Pricing Simulator — POST /api/v1/sap/pricing

Aceita payload no formato KOMV (tabela de condições de pricing do SD) e
devolve as mesmas condições preenchidas com o resultado do motor FiscalCore.

Objetivo: provar que o motor pode operar como serviço externo autoritativo
para o TAXBRA na Reforma Tributária, sem tocar no core do ERP.

Convenção de tipos de condição (Z-namespace, customer):
  ZCBS  → CBS (Contribuição sobre Bens e Serviços)
  ZIBU  → IBS-UF
  ZIBM  → IBS-Município
  ZISE  → Imposto Seletivo
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .audit_ledger import append_event
from .auth import require_role
from .db import carregar_rulesets
from .idoc_parser import IdocParseError, parse_idoc_bytes
from .models import (
    CalcularRequest,
    Destinatario,
    Estabelecimento,
    ImpostoSeletivoIn,
    Item,
    Operacao,
)
from .motor import CClassTribDesconhecido, calcular, d, q2, _fmt2, _fmt4
from .rulesets import compute_ruleset_hash, resolver_ruleset

router = APIRouter(prefix="/api/v1/sap")


# ---------------------------------------------------------------------------
# Contrato KOMV (entrada)
# ---------------------------------------------------------------------------


class KomvItem(BaseModel):
    """Uma linha de item no formato KOMV/KOMP simplificado."""
    model_config = ConfigDict(extra="forbid")

    kposn: int = Field(description="Posição do item no documento SAP (PO/SO line)")
    matnr: Optional[str] = Field(default=None, description="Material número (SAP)")
    arktx: Optional[str] = Field(default=None, description="Descrição curta do item")
    ncm: Optional[str] = None
    cClassTrib: str = Field(description="Código de classificação tributária Reforma")
    menge: str = Field(description="Quantidade (decimal em string)")
    meins: str = Field(default="EA", description="Unidade de medida SAP (EA, PC, KG, ...)")
    kbetr: str = Field(description="Valor unitário — condition rate (decimal string)")
    kwert: str = Field(description="Valor líquido da linha — condition value (decimal string)")
    impostoSeletivo: Optional[ImpostoSeletivoIn] = None


class SapPricingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vbeln: str = Field(description="Número do documento SAP (SO/PO/Invoice)")
    bukrs: Optional[str] = Field(default=None, description="Company code SAP")
    kunnr: Optional[str] = Field(default=None, description="Sold-to party (customer)")
    lifnr: Optional[str] = Field(default=None, description="Fornecedor (para compras)")
    dataOperacao: date = Field(description="Data da operação (resolve o ruleset)")
    waerk: str = Field(default="BRL", description="Moeda do documento (SAP field)")
    cnpjEmitente: str
    ufEmitente: str = Field(min_length=2, max_length=2)
    municipioIBGEEmitente: str
    ufDestino: str = Field(min_length=2, max_length=2)
    municipioIBGEDestino: str
    consumidorFinal: bool = True
    contribuinte: bool = False
    tipoOperacao: Literal["venda", "transferencia", "devolucao", "servico"] = "venda"
    itens: List[KomvItem] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Contrato KOMV (saída)
# ---------------------------------------------------------------------------


class KomvCondition(BaseModel):
    """Uma linha de condição de preço no formato KOMV enriquecido."""
    kposn: int
    stunr: int = Field(description="Passo no schema de pricing (10, 20, 30...)")
    kschl: str = Field(description="Condition type (ZCBS, ZIBU, ZIBM, ZISE)")
    vtext: str = Field(description="Descrição do condition type")
    kbetr: str = Field(description="Rate (alíquota efetiva em %)")
    krech: Literal["A", "B"] = Field(default="A", description="A=percentual, B=fixo")
    kawrt: str = Field(description="Base de cálculo da condição")
    kwert: str = Field(description="Valor calculado da condição")
    waers: str = Field(description="Moeda")


class SapPricingResponse(BaseModel):
    vbeln: str
    dataOperacao: str
    rulesetId: str
    rulesetHash: str
    motorVersao: str
    waerk: str
    conditions: List[KomvCondition]
    totals: Dict[str, str] = Field(description="netval, taxAmount, brutt")
    auditoriaId: Optional[str] = None
    schemaPricing: str = Field(
        default="ZFISC01",
        description="Nome sugerido para o pricing procedure customizado",
    )
    avisos: List[str] = []


# ---------------------------------------------------------------------------
# Adaptador KOMV → contrato interno CalcularRequest
# ---------------------------------------------------------------------------


def _komv_para_calcular(req: SapPricingRequest) -> CalcularRequest:
    """Converte payload KOMV (SAP) para o contrato interno do motor."""
    itens_internos: List[Item] = []
    for idx, linha in enumerate(req.itens, start=1):
        itens_internos.append(
            Item(
                numero=idx,  # numeração interna sequencial (KPOSN preservado abaixo)
                descricao=linha.arktx,
                ncm=linha.ncm,
                cClassTrib=linha.cClassTrib,
                quantidade=linha.menge,
                valorUnitario=linha.kbetr,
                valorItem=linha.kwert,
                impostoSeletivo=linha.impostoSeletivo,
            )
        )

    return CalcularRequest(
        referencia=req.vbeln,
        dataOperacao=req.dataOperacao,
        modo="producao",
        estabelecimento=Estabelecimento(
            cnpj=req.cnpjEmitente,
            uf=req.ufEmitente,
            municipioIBGE=req.municipioIBGEEmitente,
            regime="regular",
        ),
        destinatario=Destinatario(
            uf=req.ufDestino,
            municipioIBGE=req.municipioIBGEDestino,
            consumidorFinal=req.consumidorFinal,
            contribuinte=req.contribuinte,
        ),
        operacao=Operacao(tipo=req.tipoOperacao),
        itens=itens_internos,
    )


# ---------------------------------------------------------------------------
# Motor calculado → KOMV rows
# ---------------------------------------------------------------------------


CONDITION_DEFS = [
    # kschl,  vtext,                             stunr
    ("ZCBS", "CBS - Contribuição sobre Bens e Serviços", 100),
    ("ZIBU", "IBS - UF (partilha estadual)",              110),
    ("ZIBM", "IBS - Município (partilha municipal)",     120),
    ("ZISE", "Imposto Seletivo",                          90),
]


def _motor_para_komv(
    req: SapPricingRequest, itens_out, waerk: str
) -> tuple[List[KomvCondition], Dict[str, str]]:
    conditions: List[KomvCondition] = []

    net_total = Decimal("0")
    tax_total = Decimal("0")

    for komv_in, item_out in zip(req.itens, itens_out):
        kposn = komv_in.kposn
        base_ibscbs = item_out.base  # já string 2 casas

        # Imposto Seletivo — só aparece na saída se houver
        if item_out.impostoSeletivo is not None:
            is_out = item_out.impostoSeletivo
            conditions.append(
                KomvCondition(
                    kposn=kposn, stunr=90, kschl="ZISE",
                    vtext="Imposto Seletivo",
                    kbetr=is_out.aliquota,
                    kawrt=is_out.base,
                    kwert=is_out.valor,
                    waers=waerk,
                )
            )
            tax_total += d(is_out.valor)

        # CBS
        conditions.append(
            KomvCondition(
                kposn=kposn, stunr=100, kschl="ZCBS",
                vtext="CBS - Contribuição sobre Bens e Serviços",
                kbetr=item_out.cbs.aliquotaEfetiva,
                kawrt=base_ibscbs,
                kwert=item_out.cbs.valor,
                waers=waerk,
            )
        )
        tax_total += d(item_out.cbs.valor)

        # IBS-UF
        conditions.append(
            KomvCondition(
                kposn=kposn, stunr=110, kschl="ZIBU",
                vtext="IBS - UF (partilha estadual)",
                kbetr=item_out.ibs.uf.aliquota,
                kawrt=base_ibscbs,
                kwert=item_out.ibs.uf.valor,
                waers=waerk,
            )
        )
        tax_total += d(item_out.ibs.uf.valor)

        # IBS-Mun
        conditions.append(
            KomvCondition(
                kposn=kposn, stunr=120, kschl="ZIBM",
                vtext="IBS - Município (partilha municipal)",
                kbetr=item_out.ibs.municipio.aliquota,
                kawrt=base_ibscbs,
                kwert=item_out.ibs.municipio.valor,
                waers=waerk,
            )
        )
        tax_total += d(item_out.ibs.municipio.valor)

        # net = base sem IS (i.e., o kwert que veio da SAP)
        net_total += d(komv_in.kwert)

    totals = {
        "netVal": _fmt2(net_total),
        "taxAmount": _fmt2(tax_total),
        "grossVal": _fmt2(q2(net_total + tax_total)),
    }
    return conditions, totals


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/pricing", response_model=SapPricingResponse)
async def sap_pricing(
    req: SapPricingRequest,
    user: dict = Depends(require_role("fiscal", "admin")),
) -> SapPricingResponse:
    """Recebe payload KOMV do SAP S/4HANA e devolve as condições de preço
    preenchidas pelo motor FiscalCore (IBS/CBS/IS)."""
    rulesets = await carregar_rulesets()
    ruleset = resolver_ruleset(rulesets, req.dataOperacao)
    if ruleset is None:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "sem_ruleset_vigente",
                "dataOperacao": req.dataOperacao.isoformat(),
            },
        )
    ruleset_hash = compute_ruleset_hash(ruleset)

    # Adapta contrato KOMV → contrato do motor
    calc_req = _komv_para_calcular(req)

    try:
        itens_out, _totais, avisos = calcular(calc_req, ruleset)
    except CClassTribDesconhecido as e:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "cclasstrib_desconhecido",
                "codigo": e.codigo,
                "kposn": req.itens[e.numero_item - 1].kposn,
                "rulesetId": e.ruleset_id,
            },
        )

    conditions, totals = _motor_para_komv(req, itens_out, req.waerk)

    motor_versao = os.environ.get("MOTOR_VERSAO", "dev")

    resp = SapPricingResponse(
        vbeln=req.vbeln,
        dataOperacao=req.dataOperacao.isoformat(),
        rulesetId=ruleset["id"],
        rulesetHash=ruleset_hash,
        motorVersao=motor_versao,
        waerk=req.waerk,
        conditions=conditions,
        totals=totals,
        avisos=avisos,
    )

    # Ledger — evento auditável específico do canal SAP
    await append_event(
        action="sap.pricing",
        payload={
            "vbeln": req.vbeln,
            "bukrs": req.bukrs,
            "rulesetId": ruleset["id"],
            "taxAmount": totals["taxAmount"],
            "itens": len(req.itens),
        },
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )
    return resp


@router.get("/exemplo")
async def sap_exemplo(
    _user: dict = Depends(require_role("fiscal", "auditoria", "admin")),
) -> Dict[str, Any]:
    """Retorna um payload KOMV exemplo (os 3 casos-ouro), pronto para o botão
    'Simular chamada S/4HANA' do playground."""
    return {
        "vbeln": "SO-2026-0001234",
        "bukrs": "BR01",
        "kunnr": "0000100234",
        "dataOperacao": "2026-08-26",
        "waerk": "BRL",
        "cnpjEmitente": "12345678000190",
        "ufEmitente": "SP",
        "municipioIBGEEmitente": "3550308",
        "ufDestino": "RJ",
        "municipioIBGEDestino": "3304557",
        "consumidorFinal": True,
        "contribuinte": False,
        "tipoOperacao": "venda",
        "itens": [
            {
                "kposn": 10, "matnr": "MAT-CAD-001", "arktx": "Cadeira de escritório",
                "ncm": "94013000", "cClassTrib": "000001",
                "menge": "1.000", "meins": "PC",
                "kbetr": "1000.00", "kwert": "1000.00",
            },
            {
                "kposn": 20, "matnr": "MAT-MED-060", "arktx": "Medicamento (redução 60%)",
                "ncm": "30049099", "cClassTrib": "200052",
                "menge": "1.000", "meins": "PC",
                "kbetr": "500.00", "kwert": "500.00",
            },
            {
                "kposn": 30, "matnr": "MAT-BEB-IS", "arktx": "Bebida açucarada (IS 10%)",
                "ncm": "22021000", "cClassTrib": "000001",
                "menge": "1.000", "meins": "PC",
                "kbetr": "200.00", "kwert": "200.00",
                "impostoSeletivo": {"aliquota": "10.0000", "cst": "01"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# IDOC INVOIC02 — parse + reconciliação
# ---------------------------------------------------------------------------


_SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples")
_IDOC_SAMPLES = {
    "ok": "idoc_invoic02_ok.xml",
    "diverge": "idoc_invoic02_diverge.xml",
}


@router.get("/idoc/samples")
async def sap_idoc_listar_samples(
    _user: dict = Depends(require_role("fiscal", "auditoria", "admin")),
) -> Dict[str, Any]:
    """Lista IDOCs de amostra disponíveis."""
    return {
        "samples": [
            {"id": "ok", "nome": "IDOC convergente (3 itens, IS)", "arquivo": _IDOC_SAMPLES["ok"]},
            {"id": "diverge", "nome": "IDOC com 2 divergências propositais", "arquivo": _IDOC_SAMPLES["diverge"]},
        ]
    }


@router.get("/idoc/samples/{sample_id}")
async def sap_idoc_baixar_sample(
    sample_id: str,
    _user: dict = Depends(require_role("fiscal", "auditoria", "admin")),
):
    """Devolve o conteúdo XML de uma amostra IDOC para o front carregar."""
    nome = _IDOC_SAMPLES.get(sample_id)
    if not nome:
        raise HTTPException(status_code=404, detail={"erro": "sample_nao_encontrado"})
    caminho = os.path.join(_SAMPLES_DIR, nome)
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail={"erro": "arquivo_nao_encontrado"})
    return FileResponse(caminho, media_type="application/xml", filename=nome)


@router.post("/idoc/parse")
async def sap_idoc_parse(
    file: UploadFile = File(...),
    user: dict = Depends(require_role("fiscal", "auditoria", "admin")),
) -> Dict[str, Any]:
    """Recebe um IDOC INVOIC02 (XML) inbound do SAP e devolve estrutura
    canônica (docnum, itens KPOSN, taxes por KSCHL, summary)."""
    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=415,
            detail={"erro": "formato_invalido", "esperado": ".xml"},
        )
    content = await file.read()
    try:
        parsed = parse_idoc_bytes(content)
    except IdocParseError as e:
        raise HTTPException(
            status_code=422,
            detail={"erro": "idoc_invalido", "mensagem": str(e)},
        )

    await append_event(
        action="sap.idoc.parsed",
        payload={
            "docnum": parsed.get("docnum"),
            "belnr": parsed.get("belnr"),
            "itens": len(parsed.get("itens", [])),
        },
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )
    return parsed


# ---- Reconciliação ---------------------------------------------------------


class ReconciliarRequest(BaseModel):
    """Reconcilia um IDOC parseado (o "verdade do SAP") contra o cálculo
    autoritativo do FiscalCore. O motor recalcula usando os mesmos itens.
    """
    model_config = ConfigDict(extra="forbid")

    # Corpo do IDOC parseado (formato do /idoc/parse)
    idoc: Dict[str, Any] = Field(description="IDOC parseado (saída do /idoc/parse)")
    # Contexto fiscal para o motor recalcular
    dataOperacao: date
    cnpjEmitente: str
    ufEmitente: str = Field(min_length=2, max_length=2)
    municipioIBGEEmitente: str
    ufDestino: str = Field(min_length=2, max_length=2)
    municipioIBGEDestino: str
    consumidorFinal: bool = True
    contribuinte: bool = False
    tipoOperacao: Literal["venda", "transferencia", "devolucao", "servico"] = "venda"
    toleranciaCentavos: str = Field(
        default="0.02",
        description="Tolerância em R$ para considerar dois valores 'iguais' (padrão 2 centavos).",
    )


class DivergenciaCondicao(BaseModel):
    kposn: int
    kschl: str
    sap: Optional[str] = None      # valor que o SAP mandou (KWERT do E1EDP04)
    fiscalcore: Optional[str] = None  # valor recalculado pelo motor
    delta: Optional[str] = None       # fiscalcore - sap (com sinal)
    status: Literal["match", "diverge", "sap_faltante", "fiscalcore_faltante"]


class ReconciliarResponse(BaseModel):
    docnum: Optional[str]
    rulesetId: str
    rulesetHash: str
    totais: Dict[str, str]          # sap, fiscalcore, delta
    resumo: Dict[str, int]          # matches, divergencias
    linhas: List[DivergenciaCondicao]
    veredicto: Literal["convergente", "divergente"]
    toleranciaCentavos: str


def _map_idoc_para_calcular(
    req: ReconciliarRequest, idoc: Dict[str, Any]
) -> CalcularRequest:
    """Constrói CalcularRequest a partir do IDOC parseado."""
    itens_internos: List[Item] = []
    for idx, linha in enumerate(idoc.get("itens", []), start=1):
        cclass = linha.get("cClassTrib")
        if not cclass:
            raise HTTPException(
                status_code=422,
                detail={
                    "erro": "cClassTrib_ausente",
                    "kposn": linha.get("kposn"),
                    "hint": "adicione o segmento Z1FISC_CLASTRIB/CCLASSTRIB no IDOC",
                },
            )
        # Detecta IS a partir das taxes do IDOC
        imposto_seletivo = None
        for t in linha.get("taxes", []):
            if t.get("kschl") == "ZISE":
                aliq = t.get("msatz") or "0.0000"
                # Normaliza para 4 casas
                try:
                    aliq_dec = d(aliq)
                    aliq = f"{aliq_dec:.4f}"
                except Exception:
                    pass
                imposto_seletivo = ImpostoSeletivoIn(aliquota=aliq, cst="01")
                break

        itens_internos.append(
            Item(
                numero=idx,
                descricao=linha.get("arktx"),
                cClassTrib=cclass,
                quantidade=linha.get("menge") or "1.000",
                valorUnitario=linha.get("vprei") or linha.get("netwr") or "0.00",
                valorItem=linha.get("netwr") or "0.00",
                impostoSeletivo=imposto_seletivo,
            )
        )

    return CalcularRequest(
        referencia=idoc.get("docnum") or "SAP-IDOC",
        dataOperacao=req.dataOperacao,
        modo="producao",
        estabelecimento=Estabelecimento(
            cnpj=req.cnpjEmitente,
            uf=req.ufEmitente,
            municipioIBGE=req.municipioIBGEEmitente,
            regime="regular",
        ),
        destinatario=Destinatario(
            uf=req.ufDestino,
            municipioIBGE=req.municipioIBGEDestino,
            consumidorFinal=req.consumidorFinal,
            contribuinte=req.contribuinte,
        ),
        operacao=Operacao(tipo=req.tipoOperacao),
        itens=itens_internos,
    )


def _fiscalcore_por_kposn_kschl(
    idoc_itens: List[Dict[str, Any]], itens_out
) -> Dict[tuple, str]:
    """Mapa (kposn, kschl) → valor FiscalCore (string 2 casas)."""
    result: Dict[tuple, str] = {}
    for komv_in, item_out in zip(idoc_itens, itens_out):
        kposn = komv_in.get("kposn")
        if item_out.impostoSeletivo is not None:
            result[(kposn, "ZISE")] = item_out.impostoSeletivo.valor
        result[(kposn, "ZCBS")] = item_out.cbs.valor
        result[(kposn, "ZIBU")] = item_out.ibs.uf.valor
        result[(kposn, "ZIBM")] = item_out.ibs.municipio.valor
    return result


@router.post("/reconciliar", response_model=ReconciliarResponse)
async def sap_reconciliar(
    req: ReconciliarRequest,
    user: dict = Depends(require_role("fiscal", "auditoria", "admin")),
) -> ReconciliarResponse:
    """Compara o cálculo do SAP (extraído do IDOC) contra o recálculo
    autoritativo do FiscalCore. Devolve tabela de divergências por
    (kposn, kschl) e veredicto final."""
    rulesets = await carregar_rulesets()
    ruleset = resolver_ruleset(rulesets, req.dataOperacao)
    if ruleset is None:
        raise HTTPException(
            status_code=422,
            detail={"erro": "sem_ruleset_vigente"},
        )
    ruleset_hash = compute_ruleset_hash(ruleset)

    calc_req = _map_idoc_para_calcular(req, req.idoc)
    try:
        itens_out, _totais, _avisos = calcular(calc_req, ruleset)
    except CClassTribDesconhecido as e:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "cclasstrib_desconhecido",
                "codigo": e.codigo,
                "kposn": req.idoc["itens"][e.numero_item - 1].get("kposn"),
            },
        )

    fc_map = _fiscalcore_por_kposn_kschl(req.idoc.get("itens", []), itens_out)

    # Coleta todos os pares (kposn, kschl) do lado SAP
    sap_map: Dict[tuple, str] = {}
    for linha in req.idoc.get("itens", []):
        for t in linha.get("taxes", []):
            kschl = t.get("kschl")
            if kschl in {"ZCBS", "ZIBU", "ZIBM", "ZISE"}:
                sap_map[(linha["kposn"], kschl)] = t.get("mwsbt") or "0.00"

    # Une chaves dos dois lados
    todos = sorted(set(fc_map.keys()) | set(sap_map.keys()))

    tol = d(req.toleranciaCentavos)
    linhas: List[DivergenciaCondicao] = []
    matches = 0
    divergencias = 0
    fc_total = Decimal("0")
    sap_total = Decimal("0")

    for kposn, kschl in todos:
        sap_v = sap_map.get((kposn, kschl))
        fc_v = fc_map.get((kposn, kschl))
        if sap_v is not None:
            sap_total += d(sap_v)
        if fc_v is not None:
            fc_total += d(fc_v)

        if sap_v is None:
            linhas.append(DivergenciaCondicao(
                kposn=kposn, kschl=kschl, sap=None, fiscalcore=fc_v,
                delta=fc_v, status="sap_faltante",
            ))
            divergencias += 1
        elif fc_v is None:
            linhas.append(DivergenciaCondicao(
                kposn=kposn, kschl=kschl, sap=sap_v, fiscalcore=None,
                delta=f"-{sap_v}", status="fiscalcore_faltante",
            ))
            divergencias += 1
        else:
            delta = d(fc_v) - d(sap_v)
            status_ = "match" if abs(delta) <= tol else "diverge"
            if status_ == "match":
                matches += 1
            else:
                divergencias += 1
            linhas.append(DivergenciaCondicao(
                kposn=kposn, kschl=kschl, sap=sap_v, fiscalcore=fc_v,
                delta=_fmt2(delta), status=status_,
            ))

    veredicto = "convergente" if divergencias == 0 else "divergente"

    totais = {
        "sap": _fmt2(sap_total),
        "fiscalcore": _fmt2(fc_total),
        "delta": _fmt2(fc_total - sap_total),
    }

    await append_event(
        action="sap.reconciliar",
        payload={
            "docnum": req.idoc.get("docnum"),
            "veredicto": veredicto,
            "matches": matches,
            "divergencias": divergencias,
            "delta": totais["delta"],
        },
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )

    return ReconciliarResponse(
        docnum=req.idoc.get("docnum"),
        rulesetId=ruleset["id"],
        rulesetHash=ruleset_hash,
        totais=totais,
        resumo={"matches": matches, "divergencias": divergencias, "linhas": len(linhas)},
        linhas=linhas,
        veredicto=veredicto,
        toleranciaCentavos=_fmt2(tol),
    )
