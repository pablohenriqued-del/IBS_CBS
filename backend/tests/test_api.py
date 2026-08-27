"""Testes de integração HTTP (POST /v1/calcular via TestClient)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


REQUEST_CONTRATO = {
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


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_e2e_contrato_bate_numero_por_numero(client):
    r = client.post("/api/v1/calcular", json=REQUEST_CONTRATO)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rulesetId"] == "ruleset:2026-regime-pleno-v1"
    assert body["rulesetHash"].startswith("sha256:")
    assert body["motorVersao"]
    assert body["auditoriaId"]

    itens = body["itens"]
    assert itens[0]["cbs"]["valor"] == "88.00"
    assert itens[0]["ibs"]["valor"] == "177.00"
    assert itens[1]["cbs"]["valor"] == "17.60"
    assert itens[1]["ibs"]["valor"] == "35.40"
    assert itens[2]["impostoSeletivo"]["valor"] == "20.00"
    assert itens[2]["base"] == "220.00"
    assert itens[2]["cbs"]["valor"] == "19.36"
    assert itens[2]["ibs"]["valor"] == "38.94"

    totais = body["totais"]
    assert totais["baseTotal"] == "1720.00"
    assert totais["cbs"] == "124.96"
    assert totais["ibs"] == "251.34"
    assert totais["impostoSeletivo"] == "20.00"
    assert totais["tributosTotais"] == "376.30"


def test_sem_ruleset_vigente_422(client):
    payload = dict(REQUEST_CONTRATO)
    payload["dataOperacao"] = "2020-01-01"
    r = client.post("/api/v1/calcular", json=payload)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["erro"] == "validacao"
    assert detail["detalhes"][0]["codigo"] == "sem_ruleset_vigente"


def test_cclasstrib_desconhecido_422(client):
    payload = {**REQUEST_CONTRATO}
    payload["itens"] = [dict(REQUEST_CONTRATO["itens"][0])]
    payload["itens"][0]["cClassTrib"] = "999999"
    r = client.post("/api/v1/calcular", json=payload)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["detalhes"][0]["codigo"] == "cclasstrib_desconhecido"


def test_auditoria_reproduzivel(client):
    r = client.post("/api/v1/calcular", json=REQUEST_CONTRATO)
    audit_id = r.json()["auditoriaId"]
    r2 = client.get(f"/api/v1/auditoria/{audit_id}")
    assert r2.status_code == 200
    doc = r2.json()
    assert doc["rulesetId"] == "ruleset:2026-regime-pleno-v1"
    assert doc["input"]["referencia"] == "pedido-2026-000123"
    assert doc["output"]["totais"]["cbs"] == "124.96"


def test_rulesets_listagem(client):
    r = client.get("/api/v1/rulesets")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["rulesets"]]
    assert "ruleset:2026-fase-teste" in ids
    assert "ruleset:2026-regime-pleno-v1" in ids
