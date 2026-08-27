"""Testes de integração HTTP (agora com auth)."""
from __future__ import annotations

from .conftest import REQUEST_GOLDEN


def test_health_publico(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_calcular_publico_como_demo(client):
    # /calcular agora é público em modo demo — devolve 200 e grava com actor.role=demo
    r = client.post("/api/v1/calcular", json=REQUEST_GOLDEN)
    assert r.status_code == 200, r.text
    assert "totais" in r.json()


def test_e2e_golden_admin(admin_client):
    r = admin_client.post("/api/v1/calcular", json=REQUEST_GOLDEN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rulesetId"] == "ruleset:2026-regime-pleno-v1"
    assert body["totais"]["cbs"] == "124.96"
    assert body["totais"]["ibs"] == "251.34"
    assert body["totais"]["tributosTotais"] == "376.30"
    assert body["itens"][2]["base"] == "220.00"


def test_e2e_golden_fiscal(fiscal_client):
    r = fiscal_client.post("/api/v1/calcular", json=REQUEST_GOLDEN)
    assert r.status_code == 200
    assert r.json()["totais"]["tributosTotais"] == "376.30"


def test_auditoria_pode_calcular_publico(auditoria_client):
    # /calcular agora é público em modo demo — qualquer role pode chamar
    r = auditoria_client.post("/api/v1/calcular", json=REQUEST_GOLDEN)
    assert r.status_code == 200, r.text


def test_rulesets_publico(client):
    r = client.get("/api/v1/rulesets")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["rulesets"]]
    assert "ruleset:2026-regime-pleno-v1" in ids
