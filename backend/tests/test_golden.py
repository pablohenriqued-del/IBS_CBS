"""Testes automatizados — CASOS-OURO do contrato.

Cada teste valida NÚMERO POR NÚMERO o exemplo do contrato
(api-calcular-ibs-cbs.md §6), no ruleset `ruleset:2026-regime-pleno-v1`,
com dataOperacao=2026-08-26.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models import CalcularRequest
from app.motor import calcular
from app.rulesets import RULESETS_SEED, compute_ruleset_hash, resolver_ruleset


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def request_completo():
    return CalcularRequest.model_validate(
        {
            "referencia": "pedido-2026-000123",
            "dataOperacao": "2026-08-26",
            "modo": "producao",
            "estabelecimento": {
                "cnpj": "12345678000190",
                "uf": "SP",
                "municipioIBGE": "3550308",
                "regime": "regular",
            },
            "destinatario": {
                "uf": "RJ",
                "municipioIBGE": "3304557",
                "consumidorFinal": True,
                "contribuinte": False,
            },
            "operacao": {"tipo": "venda"},
            "itens": [
                {
                    "numero": 1,
                    "descricao": "Cadeira de escritório",
                    "ncm": "94013000",
                    "cClassTrib": "000001",
                    "quantidade": "1.00",
                    "valorUnitario": "1000.00",
                    "valorItem": "1000.00",
                },
                {
                    "numero": 2,
                    "descricao": "Medicamento (lista com redução de 60%)",
                    "ncm": "30049099",
                    "cClassTrib": "200052",
                    "quantidade": "1.00",
                    "valorUnitario": "500.00",
                    "valorItem": "500.00",
                },
                {
                    "numero": 3,
                    "descricao": "Bebida açucarada (sujeita ao IS)",
                    "ncm": "22021000",
                    "cClassTrib": "000001",
                    "quantidade": "1.00",
                    "valorUnitario": "200.00",
                    "valorItem": "200.00",
                    "impostoSeletivo": {"aliquota": "10.0000", "cst": "01"},
                },
            ],
        }
    )


@pytest.fixture
def ruleset_pleno():
    return resolver_ruleset(RULESETS_SEED, date(2026, 8, 26))


# --------------------------------------------------------------------------
# 1. Resolução do ruleset pela data
# --------------------------------------------------------------------------


def test_resolucao_ruleset_por_data():
    # Meio da fase-teste
    r = resolver_ruleset(RULESETS_SEED, date(2026, 3, 15))
    assert r["id"] == "ruleset:2026-fase-teste"

    # Regime pleno (exatamente na data do exemplo do contrato)
    r = resolver_ruleset(RULESETS_SEED, date(2026, 8, 26))
    assert r["id"] == "ruleset:2026-regime-pleno-v1"

    # Antes de qualquer ruleset: None
    r = resolver_ruleset(RULESETS_SEED, date(2025, 12, 31))
    assert r is None


def test_hash_ruleset_deterministico(ruleset_pleno):
    h1 = compute_ruleset_hash(ruleset_pleno)
    h2 = compute_ruleset_hash(ruleset_pleno)
    assert h1 == h2
    assert h1.startswith("sha256:")


# --------------------------------------------------------------------------
# 2. CASO-OURO #1 — Tributação integral (item 1 do contrato)
# --------------------------------------------------------------------------


def test_caso_ouro_1_tributacao_integral(request_completo, ruleset_pleno):
    itens, _, _ = calcular(request_completo, ruleset_pleno)
    item = itens[0]

    assert item.numero == 1
    assert item.base == "1000.00"
    assert item.impostoSeletivo is None

    # CBS
    assert item.cbs.cst == "000"
    assert item.cbs.aliquotaNominal == "8.8000"
    assert item.cbs.reducao == "0.0000"
    assert item.cbs.aliquotaEfetiva == "8.8000"
    assert item.cbs.valor == "88.00"

    # IBS
    assert item.ibs.cst == "000"
    assert item.ibs.reducao == "0.0000"
    assert item.ibs.uf.aliquota == "12.0000"
    assert item.ibs.uf.valor == "120.00"
    assert item.ibs.municipio.aliquota == "5.7000"
    assert item.ibs.municipio.valor == "57.00"
    assert item.ibs.valor == "177.00"

    assert item.totalItem == "265.00"


# --------------------------------------------------------------------------
# 3. CASO-OURO #2 — Redução de 60% via cClassTrib (item 2 do contrato)
# --------------------------------------------------------------------------


def test_caso_ouro_2_reducao_60pct(request_completo, ruleset_pleno):
    itens, _, _ = calcular(request_completo, ruleset_pleno)
    item = itens[1]

    assert item.numero == 2
    assert item.base == "500.00"
    assert item.impostoSeletivo is None

    # CBS: 8.8% × 0.4 = 3.52% → 17.60
    assert item.cbs.cst == "200"
    assert item.cbs.aliquotaNominal == "8.8000"
    assert item.cbs.reducao == "60.0000"
    assert item.cbs.aliquotaEfetiva == "3.5200"
    assert item.cbs.valor == "17.60"

    # IBS: UF 4.8% → 24.00; Mun 2.28% → 11.40
    assert item.ibs.cst == "200"
    assert item.ibs.reducao == "60.0000"
    assert item.ibs.uf.aliquota == "4.8000"
    assert item.ibs.uf.valor == "24.00"
    assert item.ibs.municipio.aliquota == "2.2800"
    assert item.ibs.municipio.valor == "11.40"
    assert item.ibs.valor == "35.40"

    assert item.totalItem == "53.00"


# --------------------------------------------------------------------------
# 4. CASO-OURO #3 — Imposto Seletivo entra na base (item 3 do contrato)
# --------------------------------------------------------------------------


def test_caso_ouro_3_is_na_base(request_completo, ruleset_pleno):
    itens, _, _ = calcular(request_completo, ruleset_pleno)
    item = itens[2]

    assert item.numero == 3

    # IS antes de IBS/CBS
    assert item.impostoSeletivo is not None
    assert item.impostoSeletivo.base == "200.00"
    assert item.impostoSeletivo.aliquota == "10.0000"
    assert item.impostoSeletivo.valor == "20.00"

    # Base IBS/CBS = 200 + 20 = 220 (IS ENTRA na base)
    assert item.base == "220.00"

    # CBS = 220 × 8.8% = 19.36
    assert item.cbs.valor == "19.36"
    assert item.cbs.aliquotaEfetiva == "8.8000"

    # IBS-UF = 220 × 12% = 26.40; IBS-Mun = 220 × 5.7% = 12.54
    assert item.ibs.uf.valor == "26.40"
    assert item.ibs.municipio.valor == "12.54"
    assert item.ibs.valor == "38.94"

    # totalItem = IS + CBS + IBS = 20 + 19.36 + 38.94 = 78.30
    assert item.totalItem == "78.30"


# --------------------------------------------------------------------------
# 5. TOTAIS agregados batem número por número com o contrato
# --------------------------------------------------------------------------


def test_totais_batem_com_contrato(request_completo, ruleset_pleno):
    _, totais, _ = calcular(request_completo, ruleset_pleno)

    assert totais.baseTotal == "1720.00"
    assert totais.impostoSeletivo == "20.00"
    assert totais.cbs == "124.96"
    assert totais.ibsUF == "170.40"
    assert totais.ibsMunicipio == "80.94"
    assert totais.ibs == "251.34"
    # tributosTotais = CBS + IBS (IS aparece separado, conforme contrato)
    assert totais.tributosTotais == "376.30"


# --------------------------------------------------------------------------
# 6. Determinismo: dois cálculos idênticos → mesmo resultado
# --------------------------------------------------------------------------


def test_determinismo(request_completo, ruleset_pleno):
    r1_itens, r1_totais, _ = calcular(request_completo, ruleset_pleno)
    r2_itens, r2_totais, _ = calcular(request_completo, ruleset_pleno)

    assert r1_totais.model_dump() == r2_totais.model_dump()
    for a, b in zip(r1_itens, r2_itens):
        assert a.model_dump() == b.model_dump()


# --------------------------------------------------------------------------
# 7. Nunca usa float (property test rápido)
# --------------------------------------------------------------------------


def test_precisao_decimal_sem_float():
    from app.motor import d

    # 0.1 + 0.2 em Decimal deve ser exato
    assert d("0.1") + d("0.2") == Decimal("0.3")


# --------------------------------------------------------------------------
# 8. cClassTrib desconhecido → falha explícita (regra de ouro)
# --------------------------------------------------------------------------


def test_cclasstrib_desconhecido_falha(request_completo, ruleset_pleno):
    from app.motor import CClassTribDesconhecido

    req = request_completo.model_copy(deep=True)
    req.itens[0].cClassTrib = "999999"
    with pytest.raises(CClassTribDesconhecido):
        calcular(req, ruleset_pleno)


# --------------------------------------------------------------------------
# 9. Fase-teste: 1000 × 0,9% = 9,00 CBS e 1000 × 0,1% = 1,00 IBS
# --------------------------------------------------------------------------


def test_fase_teste_ruleset():
    ruleset = resolver_ruleset(RULESETS_SEED, date(2026, 3, 15))
    req = CalcularRequest.model_validate(
        {
            "referencia": "teste-fase",
            "dataOperacao": "2026-03-15",
            "modo": "producao",
            "estabelecimento": {
                "cnpj": "12345678000190",
                "uf": "SP",
                "municipioIBGE": "3550308",
                "regime": "regular",
            },
            "destinatario": {
                "uf": "SP",
                "municipioIBGE": "3550308",
                "consumidorFinal": True,
                "contribuinte": False,
            },
            "operacao": {"tipo": "venda"},
            "itens": [
                {
                    "numero": 1,
                    "cClassTrib": "000001",
                    "quantidade": "1.00",
                    "valorUnitario": "1000.00",
                    "valorItem": "1000.00",
                }
            ],
        }
    )
    itens, totais, _ = calcular(req, ruleset)
    assert itens[0].base == "1000.00"
    assert itens[0].cbs.valor == "9.00"
    assert itens[0].ibs.uf.valor == "1.00"
    assert itens[0].ibs.municipio.valor == "0.00"
    assert itens[0].ibs.valor == "1.00"
    assert totais.tributosTotais == "10.00"


# --------------------------------------------------------------------------
# 10. Descontos e acréscimos afetam a base corretamente
# --------------------------------------------------------------------------


def test_desconto_e_acrescimos_na_base():
    ruleset = resolver_ruleset(RULESETS_SEED, date(2026, 8, 26))
    req = CalcularRequest.model_validate(
        {
            "referencia": "teste-base",
            "dataOperacao": "2026-08-26",
            "modo": "producao",
            "estabelecimento": {
                "cnpj": "12345678000190",
                "uf": "SP",
                "municipioIBGE": "3550308",
                "regime": "regular",
            },
            "destinatario": {
                "uf": "SP",
                "municipioIBGE": "3550308",
                "consumidorFinal": True,
                "contribuinte": False,
            },
            "operacao": {"tipo": "venda"},
            "itens": [
                {
                    "numero": 1,
                    "cClassTrib": "000001",
                    "quantidade": "1.00",
                    "valorUnitario": "1000.00",
                    "valorItem": "1000.00",
                    "descontoIncondicional": "100.00",
                    "acrescimos": {
                        "frete": "50.00",
                        "seguro": "10.00",
                        "outrasDespesas": "40.00",
                    },
                }
            ],
        }
    )
    itens, _, _ = calcular(req, ruleset)
    # base = 1000 - 100 + 50 + 10 + 40 = 1000
    assert itens[0].base == "1000.00"
    assert itens[0].cbs.valor == "88.00"
    assert itens[0].ibs.valor == "177.00"
