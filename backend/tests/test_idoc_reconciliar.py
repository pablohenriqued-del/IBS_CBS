"""Testes do parser IDOC e do endpoint /sap/reconciliar."""
from __future__ import annotations

import os
from pathlib import Path

from app.idoc_parser import parse_idoc_bytes, IdocParseError

SAMPLES = Path(__file__).parent.parent / "samples"


# -------- Parser puro (unit) --------


def test_parse_idoc_ok_extrai_estrutura_canonica():
    xml = (SAMPLES / "idoc_invoic02_ok.xml").read_bytes()
    parsed = parse_idoc_bytes(xml)

    assert parsed["mestyp"] == "INVOIC"
    assert parsed["idoctp"] == "INVOIC02"
    assert parsed["docnum"] == "0000000012345"
    assert parsed["currency"] == "BRL"
    assert parsed["belnr"] == "0001234567"

    assert len(parsed["itens"]) == 3
    # Item 10 — Cadeira
    it10 = parsed["itens"][0]
    assert it10["kposn"] == 10
    assert it10["matnr"] == "MAT-CAD-001"
    assert it10["netwr"] == "1000.00"
    assert it10["cClassTrib"] == "000001"
    assert len(it10["taxes"]) == 3
    kschls = {t["kschl"] for t in it10["taxes"]}
    assert kschls == {"ZCBS", "ZIBU", "ZIBM"}
    # Item 30 — Bebida com IS
    it30 = parsed["itens"][2]
    assert it30["kposn"] == 30
    assert {t["kschl"] for t in it30["taxes"]} == {"ZISE", "ZCBS", "ZIBU", "ZIBM"}

    # Summary
    assert parsed["summary"]["net"] == "1700.00"
    assert parsed["summary"]["tax"] == "396.30"
    assert parsed["summary"]["gross"] == "2096.30"


def test_parse_idoc_xml_invalido_lanca():
    try:
        parse_idoc_bytes(b"<INVOIC02><IDOC><brokenxml")
    except IdocParseError as e:
        assert "XML" in str(e)
    else:
        raise AssertionError("deveria ter lançado IdocParseError")


def test_parse_idoc_sem_itens_lanca():
    minimal = b"""<?xml version="1.0"?><INVOIC02><IDOC>
      <EDI_DC40><DOCNUM>1</DOCNUM></EDI_DC40>
      <E1EDK01><CURCY>BRL</CURCY></E1EDK01>
    </IDOC></INVOIC02>"""
    try:
        parse_idoc_bytes(minimal)
    except IdocParseError as e:
        assert "item" in str(e).lower()
    else:
        raise AssertionError("deveria ter lançado por falta de <E1EDP01>")


# -------- Endpoint /sap/idoc/parse --------


def test_endpoint_idoc_parse_requer_auth(client):
    xml = (SAMPLES / "idoc_invoic02_ok.xml").read_bytes()
    r = client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.xml", xml, "application/xml")},
    )
    assert r.status_code == 401


def test_endpoint_idoc_parse_ok(admin_client):
    xml = (SAMPLES / "idoc_invoic02_ok.xml").read_bytes()
    r = admin_client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.xml", xml, "application/xml")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["docnum"] == "0000000012345"
    assert len(body["itens"]) == 3


def test_endpoint_idoc_parse_recusa_nao_xml(admin_client):
    r = admin_client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.txt", b"nao eh xml", "text/plain")},
    )
    assert r.status_code == 415


def test_endpoint_idoc_parse_gera_evento_ledger(admin_client):
    xml = (SAMPLES / "idoc_invoic02_ok.xml").read_bytes()
    admin_client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.xml", xml, "application/xml")},
    )
    r = admin_client.get("/api/v1/auditoria/ledger?limit=5")
    assert r.status_code == 200
    eventos = r.json()["eventos"]
    assert any(e["action"] == "sap.idoc.parsed" for e in eventos)


# -------- Endpoint /sap/reconciliar --------


def _contexto_padrao(idoc_dict):
    return {
        "idoc": idoc_dict,
        "dataOperacao": "2026-08-26",
        "cnpjEmitente": "12345678000190",
        "ufEmitente": "SP",
        "municipioIBGEEmitente": "3550308",
        "ufDestino": "RJ",
        "municipioIBGEDestino": "3304557",
        "consumidorFinal": True,
        "contribuinte": False,
    }


def test_reconciliar_idoc_ok_veredicto_convergente(admin_client):
    xml = (SAMPLES / "idoc_invoic02_ok.xml").read_bytes()
    r1 = admin_client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.xml", xml, "application/xml")},
    )
    assert r1.status_code == 200
    idoc = r1.json()

    r2 = admin_client.post("/api/v1/sap/reconciliar", json=_contexto_padrao(idoc))
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["veredicto"] == "convergente"
    assert body["resumo"]["divergencias"] == 0
    assert body["totais"]["sap"] == "396.30"
    assert body["totais"]["fiscalcore"] == "396.30"
    assert body["totais"]["delta"] == "0.00"


def test_reconciliar_idoc_divergente_aponta_linhas_erradas(admin_client):
    xml = (SAMPLES / "idoc_invoic02_diverge.xml").read_bytes()
    r1 = admin_client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.xml", xml, "application/xml")},
    )
    idoc = r1.json()

    r2 = admin_client.post("/api/v1/sap/reconciliar", json=_contexto_padrao(idoc))
    assert r2.status_code == 200
    body = r2.json()
    assert body["veredicto"] == "divergente"
    assert body["resumo"]["divergencias"] >= 2

    # Deve marcar KPOSN 10 · ZCBS (SAP=90.00 vs FiscalCore=88.00) como diverge
    divs = [
        L for L in body["linhas"]
        if L["kposn"] == 10 and L["kschl"] == "ZCBS"
    ]
    assert len(divs) == 1 and divs[0]["status"] == "diverge"
    assert divs[0]["sap"] == "90.00"
    assert divs[0]["fiscalcore"] == "88.00"
    assert divs[0]["delta"] == "-2.00"

    # E KPOSN 30 · ZCBS (SAP não aplicou IS na base — 17.60 vs 19.36)
    divs2 = [
        L for L in body["linhas"]
        if L["kposn"] == 30 and L["kschl"] == "ZCBS"
    ]
    assert len(divs2) == 1 and divs2[0]["status"] == "diverge"


def test_reconciliar_grava_evento_com_veredicto(admin_client):
    xml = (SAMPLES / "idoc_invoic02_ok.xml").read_bytes()
    idoc = admin_client.post(
        "/api/v1/sap/idoc/parse",
        files={"file": ("idoc.xml", xml, "application/xml")},
    ).json()
    admin_client.post("/api/v1/sap/reconciliar", json=_contexto_padrao(idoc))
    r = admin_client.get("/api/v1/auditoria/ledger?limit=5")
    eventos = r.json()["eventos"]
    rec = next((e for e in eventos if e["action"] == "sap.reconciliar"), None)
    assert rec is not None
    assert rec["payload"]["veredicto"] == "convergente"
