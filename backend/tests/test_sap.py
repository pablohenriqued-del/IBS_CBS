"""Testes do módulo SAP-sim (POST /api/v1/sap/pricing).

Valida que:
  1. O payload KOMV é aceito e roteado.
  2. As alíquotas e valores gerados batem com o motor (mesmos casos-ouro).
  3. As condition types SAP são geradas corretamente (ZCBS, ZIBU, ZIBM, ZISE).
  4. O ledger registra um evento sap.pricing.
"""
from __future__ import annotations

from decimal import Decimal


def _payload_golden():
    return {
        "vbeln": "SO-TEST-0001",
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
            {"kposn": 10, "matnr": "MAT-CAD", "arktx": "Cadeira",
             "ncm": "94013000", "cClassTrib": "000001",
             "menge": "1.000", "meins": "PC",
             "kbetr": "1000.00", "kwert": "1000.00"},
            {"kposn": 20, "matnr": "MAT-MED", "arktx": "Medicamento",
             "ncm": "30049099", "cClassTrib": "200052",
             "menge": "1.000", "meins": "PC",
             "kbetr": "500.00", "kwert": "500.00"},
            {"kposn": 30, "matnr": "MAT-BEB", "arktx": "Bebida",
             "ncm": "22021000", "cClassTrib": "000001",
             "menge": "1.000", "meins": "PC",
             "kbetr": "200.00", "kwert": "200.00",
             "impostoSeletivo": {"aliquota": "10.0000", "cst": "01"}},
        ],
    }


def test_sap_pricing_requer_auth(client):
    r = client.post("/api/v1/sap/pricing", json=_payload_golden())
    assert r.status_code == 401, r.text


def test_sap_pricing_golden_bate_byte_a_byte(admin_client):
    r = admin_client.post("/api/v1/sap/pricing", json=_payload_golden())
    assert r.status_code == 200, r.text
    body = r.json()

    # Cabeçalho SAP
    assert body["vbeln"] == "SO-TEST-0001"
    assert body["waerk"] == "BRL"
    assert body["schemaPricing"] == "ZFISC01"
    assert body["rulesetId"] == "ruleset:2026-regime-pleno-v1"
    assert body["rulesetHash"].startswith("sha256:")
    assert len(body["rulesetHash"]) == 71  # 'sha256:' + 64 hex

    conds = body["conditions"]
    # Item 10 (integral): sem IS, então só ZCBS+ZIBU+ZIBM = 3 linhas
    # Item 20 (redução): 3 linhas
    # Item 30 (com IS): ZISE + ZCBS + ZIBU + ZIBM = 4 linhas
    assert len(conds) == 3 + 3 + 4

    by_item = {}
    for c in conds:
        by_item.setdefault(c["kposn"], {})[c["kschl"]] = c

    # Item 10 — cadeira R$ 1.000
    assert by_item[10]["ZCBS"]["kwert"] == "88.00"
    assert by_item[10]["ZIBU"]["kwert"] == "120.00"
    assert by_item[10]["ZIBM"]["kwert"] == "57.00"
    assert by_item[10]["ZCBS"]["kawrt"] == "1000.00"
    assert "ZISE" not in by_item[10]

    # Item 20 — medicamento R$ 500 com redução 60% (fator 0.40)
    assert by_item[20]["ZCBS"]["kwert"] == "17.60"
    # IBS-UF = 500 * 12% * 0.40 = 24.00; IBS-Mun = 500 * 5.7% * 0.40 = 11.40
    assert by_item[20]["ZIBU"]["kwert"] == "24.00"
    assert by_item[20]["ZIBM"]["kwert"] == "11.40"

    # Item 30 — bebida R$ 200 com IS 10%. IS = 20; base IBS/CBS = 220
    assert by_item[30]["ZISE"]["kwert"] == "20.00"
    assert by_item[30]["ZCBS"]["kawrt"] == "220.00"
    # CBS = 220 * 8.8% = 19.36
    assert by_item[30]["ZCBS"]["kwert"] == "19.36"
    # IBS-UF = 220 * 12% = 26.40; IBS-Mun = 220 * 5.7% = 12.54
    assert by_item[30]["ZIBU"]["kwert"] == "26.40"
    assert by_item[30]["ZIBM"]["kwert"] == "12.54"

    # Totais
    # net = 1000 + 500 + 200 = 1700
    assert body["totals"]["netVal"] == "1700.00"
    # tax = 88+120+57 + 17.60+24+11.40 + 20+19.36+26.40+12.54 = 396.30
    assert body["totals"]["taxAmount"] == "396.30"
    assert body["totals"]["grossVal"] == "2096.30"


def test_sap_pricing_stunr_ordem_pricing_schema(admin_client):
    r = admin_client.post("/api/v1/sap/pricing", json=_payload_golden())
    assert r.status_code == 200
    conds = r.json()["conditions"]
    # Todas as condições ZISE têm stunr 90 (antes do CBS/IBS)
    for c in conds:
        if c["kschl"] == "ZISE":
            assert c["stunr"] == 90
        elif c["kschl"] == "ZCBS":
            assert c["stunr"] == 100
        elif c["kschl"] == "ZIBU":
            assert c["stunr"] == 110
        elif c["kschl"] == "ZIBM":
            assert c["stunr"] == 120


def test_sap_exemplo_endpoint_retorna_payload_valido(admin_client):
    r = admin_client.get("/api/v1/sap/exemplo")
    assert r.status_code == 200
    exemplo = r.json()
    # o exemplo devolvido tem que ser aceito pelo /pricing
    r2 = admin_client.post("/api/v1/sap/pricing", json=exemplo)
    assert r2.status_code == 200, r2.text
    assert r2.json()["totals"]["taxAmount"] == "396.30"


def test_sap_pricing_cclasstrib_desconhecido_retorna_422_com_kposn(admin_client):
    payload = _payload_golden()
    payload["itens"][1]["cClassTrib"] = "999999"
    r = admin_client.post("/api/v1/sap/pricing", json=payload)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["erro"] == "cclasstrib_desconhecido"
    assert detail["kposn"] == 20  # devolve o KPOSN do SAP, não o índice interno


def test_sap_pricing_gera_evento_no_ledger(admin_client):
    r = admin_client.post("/api/v1/sap/pricing", json=_payload_golden())
    assert r.status_code == 200
    # Verifica se o ledger tem o evento
    r_led = admin_client.get("/api/v1/auditoria/ledger?limit=5")
    assert r_led.status_code == 200
    eventos = r_led.json()["eventos"]
    assert any(e["action"] == "sap.pricing" for e in eventos), eventos
