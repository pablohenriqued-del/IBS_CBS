"""External URL tests via REACT_APP_BACKEND_URL — validates ingress + Mongo."""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://tributaria-core.preview.emergentagent.com").rstrip("/")

REQUEST_CONTRATO = {
    "referencia": "pedido-2026-000123",
    "dataOperacao": "2026-08-26",
    "modo": "producao",
    "estabelecimento": {"cnpj": "12345678000190", "uf": "SP", "municipioIBGE": "3550308", "regime": "regular"},
    "destinatario": {"uf": "RJ", "municipioIBGE": "3304557", "consumidorFinal": True, "contribuinte": False},
    "operacao": {"tipo": "venda"},
    "itens": [
        {"numero": 1, "descricao": "Cadeira", "ncm": "94013000", "cClassTrib": "000001",
         "quantidade": "1.00", "valorUnitario": "1000.00", "valorItem": "1000.00"},
        {"numero": 2, "descricao": "Medicamento", "ncm": "30049099", "cClassTrib": "200052",
         "quantidade": "1.00", "valorUnitario": "500.00", "valorItem": "500.00"},
        {"numero": 3, "descricao": "Bebida", "ncm": "22021000", "cClassTrib": "000001",
         "quantidade": "1.00", "valorUnitario": "200.00", "valorItem": "200.00",
         "impostoSeletivo": {"aliquota": "10.0000", "cst": "01"}},
    ],
}


@pytest.fixture
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_health(api):
    r = api.get(f"{BASE_URL}/api/v1/health", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["servico"] == "fiscalcore-motor"


def test_rulesets_list(api):
    r = api.get(f"{BASE_URL}/api/v1/rulesets", timeout=15)
    assert r.status_code == 200
    data = r.json()
    ids = [x["id"] for x in data["rulesets"]]
    assert "ruleset:2026-fase-teste" in ids
    assert "ruleset:2026-regime-pleno-v1" in ids
    fase = next(x for x in data["rulesets"] if x["id"] == "ruleset:2026-fase-teste")
    assert fase["vigenciaInicio"] == "2026-01-01"
    assert fase["vigenciaFim"] == "2026-06-30"
    pleno = next(x for x in data["rulesets"] if x["id"] == "ruleset:2026-regime-pleno-v1")
    assert pleno["vigenciaInicio"] == "2026-07-01"
    assert pleno.get("vigenciaFim") is None


def test_calcular_golden_bytes(api):
    r = api.post(f"{BASE_URL}/api/v1/calcular", json=REQUEST_CONTRATO, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rulesetId"] == "ruleset:2026-regime-pleno-v1"
    assert body["rulesetHash"].startswith("sha256:")
    assert body["motorVersao"]
    assert body["auditoriaId"]

    it = body["itens"]
    # item 1
    assert it[0]["base"] == "1000.00"
    assert it[0]["cbs"]["valor"] == "88.00"
    assert it[0]["ibs"]["uf"]["valor"] == "120.00"
    assert it[0]["ibs"]["municipio"]["valor"] == "57.00"
    assert it[0]["ibs"]["valor"] == "177.00"
    assert it[0]["totalItem"] == "265.00"
    # item 2
    assert it[1]["base"] == "500.00"
    assert it[1]["cbs"]["aliquotaEfetiva"] == "3.5200"
    assert it[1]["cbs"]["valor"] == "17.60"
    assert it[1]["ibs"]["uf"]["valor"] == "24.00"
    assert it[1]["ibs"]["municipio"]["valor"] == "11.40"
    assert it[1]["ibs"]["valor"] == "35.40"
    assert it[1]["totalItem"] == "53.00"
    # item 3
    assert it[2]["impostoSeletivo"]["valor"] == "20.00"
    assert it[2]["base"] == "220.00"
    assert it[2]["cbs"]["valor"] == "19.36"
    assert it[2]["ibs"]["uf"]["valor"] == "26.40"
    assert it[2]["ibs"]["municipio"]["valor"] == "12.54"
    assert it[2]["ibs"]["valor"] == "38.94"
    assert it[2]["totalItem"] == "78.30"

    t = body["totais"]
    assert t["baseTotal"] == "1720.00"
    assert t["cbs"] == "124.96"
    assert t["ibsUF"] == "170.40"
    assert t["ibsMunicipio"] == "80.94"
    assert t["ibs"] == "251.34"
    assert t["impostoSeletivo"] == "20.00"
    assert t["tributosTotais"] == "376.30"

    # memoriaCalculo per item, >=3 lines
    for item in it:
        mem = item.get("memoriaCalculo") or []
        assert len(mem) >= 3
        joined = " ".join(str(x) for x in mem)
        assert "Base" in joined or "base" in joined


def test_determinismo_via_http(api):
    r1 = api.post(f"{BASE_URL}/api/v1/calcular", json=REQUEST_CONTRATO, timeout=30).json()
    r2 = api.post(f"{BASE_URL}/api/v1/calcular", json=REQUEST_CONTRATO, timeout=30).json()
    # numeric fields must match byte for byte
    assert r1["totais"] == r2["totais"]
    for a, b in zip(r1["itens"], r2["itens"]):
        for k in ("base", "totalItem"):
            assert a[k] == b[k]
        assert a["cbs"] == b["cbs"]
        assert a["ibs"] == b["ibs"]


def test_auditoria_persistida(api):
    r = api.post(f"{BASE_URL}/api/v1/calcular", json=REQUEST_CONTRATO, timeout=30).json()
    audit_id = r["auditoriaId"]
    r2 = api.get(f"{BASE_URL}/api/v1/auditoria/{audit_id}", timeout=15)
    assert r2.status_code == 200
    doc = r2.json()
    assert doc["rulesetId"] == "ruleset:2026-regime-pleno-v1"
    assert doc["input"]["referencia"] == "pedido-2026-000123"
    assert doc["output"]["totais"]["cbs"] == "124.96"
    assert doc["output"]["totais"]["tributosTotais"] == "376.30"


def test_sem_ruleset_vigente(api):
    payload = dict(REQUEST_CONTRATO); payload["dataOperacao"] = "2020-01-01"
    r = api.post(f"{BASE_URL}/api/v1/calcular", json=payload, timeout=15)
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["detalhes"][0]["codigo"] == "sem_ruleset_vigente"


def test_cclasstrib_desconhecido(api):
    payload = {**REQUEST_CONTRATO, "itens": [dict(REQUEST_CONTRATO["itens"][0])]}
    payload["itens"][0]["cClassTrib"] = "999999"
    r = api.post(f"{BASE_URL}/api/v1/calcular", json=payload, timeout=15)
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["detalhes"][0]["codigo"] == "cclasstrib_desconhecido"


def test_fase_teste_period(api):
    payload = {**REQUEST_CONTRATO, "dataOperacao": "2026-03-15",
               "itens": [{"numero": 1, "cClassTrib": "000001", "quantidade": "1.00",
                          "valorUnitario": "1000.00", "valorItem": "1000.00"}]}
    r = api.post(f"{BASE_URL}/api/v1/calcular", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rulesetId"] == "ruleset:2026-fase-teste"
    assert body["itens"][0]["cbs"]["valor"] == "9.00"


def test_desconto_e_acrescimos(api):
    payload = {**REQUEST_CONTRATO, "itens": [{
        "numero": 1, "cClassTrib": "000001", "quantidade": "1.00",
        "valorUnitario": "1000.00", "valorItem": "1000.00",
        "descontoIncondicional": "100.00",
        "acrescimos": {"frete": "50.00", "seguro": "10.00", "outrasDespesas": "40.00"},
    }]}
    r = api.post(f"{BASE_URL}/api/v1/calcular", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["itens"][0]["base"] == "1000.00"
    assert body["itens"][0]["cbs"]["valor"] == "88.00"
