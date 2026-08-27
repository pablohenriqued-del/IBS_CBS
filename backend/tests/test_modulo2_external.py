"""External smoke tests for Module 2 hitting REACT_APP_BACKEND_URL (ingress + Mongo)."""
from __future__ import annotations

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://tributaria-core.preview.emergentagent.com",
).rstrip("/")

ADMIN_EMAIL = "admin@fiscalcore.local"
ADMIN_PASSWORD = "FiscalCore@2026"


def _make_xml(chave: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00"><NFe><infNFe versao="4.00" Id="NFe{chave}">
 <ide><cUF>35</cUF><natOp>Venda</natOp><dhEmi>2026-08-26T10:00:00-03:00</dhEmi></ide>
 <emit><CNPJ>12345678000190</CNPJ><xNome>Sony Music</xNome><enderEmit><UF>SP</UF></enderEmit></emit>
 <dest><CNPJ>98765432000100</CNPJ><xNome>Cliente</xNome><enderDest><UF>RJ</UF></enderDest></dest>
 <det nItem="1">
  <prod><cProd>CAD001</cProd><xProd>Cadeira</xProd><NCM>94013000</NCM>
   <qCom>1.00</qCom><vUnCom>1000.00</vUnCom><vProd>1000.00</vProd></prod>
  <imposto><IBSCBS><cClassTrib>000001</cClassTrib><vBC>1000.00</vBC></IBSCBS></imposto>
 </det>
</infNFe></NFe></nfeProc>""".encode("utf-8")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "admin"
    assert body["email"] == ADMIN_EMAIL
    tok = body["access_token"]
    assert isinstance(tok, str) and len(tok) > 20
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _register(admin_headers, role: str):
    email = f"ext-{role}-{uuid.uuid4().hex[:8]}@fiscalcore.local"
    password = "ExtTest@2026"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": f"Ext {role}", "role": role},
        headers=admin_headers,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    r2 = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert r2.status_code == 200
    return {"Authorization": f"Bearer {r2.json()['access_token']}"}


@pytest.fixture(scope="module")
def fiscal_headers(admin_headers):
    return _register(admin_headers, "fiscal")


@pytest.fixture(scope="module")
def auditoria_headers(admin_headers):
    return _register(admin_headers, "auditoria")


# ---------- auth ----------


def test_login_wrong_password_401():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "nope"},
        timeout=15,
    )
    assert r.status_code == 401


def test_me_without_bearer_401():
    r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 401


def test_me_with_bearer_ok(admin_headers):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"


def test_register_fiscal_forbidden(fiscal_headers):
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": f"nope-{uuid.uuid4().hex[:6]}@fiscalcore.local",
            "password": "Senha@1234",
            "name": "x",
            "role": "fiscal",
        },
        headers=fiscal_headers,
        timeout=15,
    )
    assert r.status_code == 403


# ---------- golden ----------

REQUEST_GOLDEN = {
    "referencia": "pedido-2026-000123",
    "dataOperacao": "2026-08-26",
    "modo": "producao",
    "estabelecimento": {"cnpj": "12345678000190", "uf": "SP", "municipioIBGE": "3550308", "regime": "regular"},
    "destinatario": {"uf": "RJ", "municipioIBGE": "3304557", "consumidorFinal": True, "contribuinte": False},
    "operacao": {"tipo": "venda"},
    "itens": [
        {"numero": 1, "cClassTrib": "000001", "quantidade": "1.00", "valorUnitario": "1000.00", "valorItem": "1000.00"},
        {"numero": 2, "cClassTrib": "200052", "quantidade": "1.00", "valorUnitario": "500.00", "valorItem": "500.00"},
        {"numero": 3, "cClassTrib": "000001", "quantidade": "1.00", "valorUnitario": "200.00", "valorItem": "200.00",
         "impostoSeletivo": {"aliquota": "10.0000", "cst": "01"}},
    ],
}


def test_calcular_sem_auth_401():
    r = requests.post(f"{BASE_URL}/api/v1/calcular", json=REQUEST_GOLDEN, timeout=20)
    assert r.status_code == 401


def test_calcular_golden(admin_headers):
    r = requests.post(f"{BASE_URL}/api/v1/calcular", json=REQUEST_GOLDEN, headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    totais = body["totais"]
    assert totais["baseTotal"] == "1720.00"
    assert totais["cbs"] == "124.96"
    assert totais["ibs"] == "251.34"
    assert totais["tributosTotais"] == "376.30"
    itens = body["itens"]
    assert itens[0]["totalItem"] == "265.00"
    assert itens[1]["totalItem"] == "53.00"
    assert itens[2]["totalItem"] == "78.30"


# ---------- ingestão ----------


def test_importar_saida_ok(fiscal_headers):
    chave = "35260812345678000190550010000001" + uuid.uuid4().hex[:12].upper()[:12]
    # chave must be 44 digits — use numeric
    chave = "35260812345678000190550010000001" + str(uuid.uuid4().int)[:12]
    xml = _make_xml(chave)
    r = requests.post(
        f"{BASE_URL}/api/v1/documentos/importar",
        headers=fiscal_headers,
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chaveAcesso"] == chave
    assert body["direcao"] == "saida"
    assert body["totais"]["cbs"] == "88.00"
    assert body["totais"]["ibs"] == "177.00"


def test_importar_duplicado_409(fiscal_headers):
    chave = "35260812345678000190550010000002" + str(uuid.uuid4().int)[:12]
    xml = _make_xml(chave)
    r1 = requests.post(
        f"{BASE_URL}/api/v1/documentos/importar",
        headers=fiscal_headers,
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
        timeout=30,
    )
    assert r1.status_code == 200
    r2 = requests.post(
        f"{BASE_URL}/api/v1/documentos/importar",
        headers=fiscal_headers,
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
        timeout=30,
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["erro"] == "documento_ja_importado"


def test_importar_xml_invalido_422(fiscal_headers):
    r = requests.post(
        f"{BASE_URL}/api/v1/documentos/importar",
        headers=fiscal_headers,
        files={"arquivo": ("bad.xml", b"<not-a-nfe/>", "application/xml")},
        data={"direcao": "saida"},
        timeout=15,
    )
    assert r.status_code == 422


def test_importar_auditoria_403(auditoria_headers):
    chave = "35260812345678000190550010000003" + str(uuid.uuid4().int)[:12]
    xml = _make_xml(chave)
    r = requests.post(
        f"{BASE_URL}/api/v1/documentos/importar",
        headers=auditoria_headers,
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
        timeout=15,
    )
    assert r.status_code == 403


# ---------- apuração ----------


def test_apuracao_periodo(fiscal_headers):
    r = requests.post(
        f"{BASE_URL}/api/v1/apuracao/periodo",
        headers=fiscal_headers,
        json={"dataInicio": "2026-08-01", "dataFim": "2026-08-31"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "debitos" in body and "creditos" in body and "apurado" in body
    for k in ("cbs", "ibs"):
        assert k in body["debitos"]
        assert k in body["creditos"]
        assert k in body["apurado"]


# ---------- audit ledger ----------


def test_ledger_fiscal_forbidden(fiscal_headers):
    r = requests.get(f"{BASE_URL}/api/v1/auditoria/ledger", headers=fiscal_headers, timeout=15)
    assert r.status_code == 403


def test_ledger_auditoria_ok(auditoria_headers):
    r = requests.get(f"{BASE_URL}/api/v1/auditoria/ledger?limit=20", headers=auditoria_headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "eventos" in body
    eventos = body["eventos"]
    assert len(eventos) >= 1
    # eventos vêm ordenados por seq desc
    seqs = [e["seq"] for e in eventos]
    assert seqs == sorted(seqs, reverse=True)


def test_ledger_hash_chain(admin_headers):
    r = requests.get(f"{BASE_URL}/api/v1/auditoria/ledger?limit=50", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    eventos = sorted(r.json()["eventos"], key=lambda e: e["seq"])
    for i, e in enumerate(eventos):
        if e["seq"] == 1:
            assert e["prev_hash"] in (None, "")
        elif i > 0 and eventos[i - 1]["seq"] == e["seq"] - 1:
            assert e["prev_hash"] == eventos[i - 1]["hash"]


def test_ledger_verificar_ok(admin_headers):
    r = requests.get(f"{BASE_URL}/api/v1/auditoria/verificar", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["broken_at"] is None
    assert body["total"] >= 1
