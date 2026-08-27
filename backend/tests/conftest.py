"""Fixtures compartilhadas — cliente autenticado como admin."""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_client(client):
    """Retorna client já autenticado como admin (via Bearer header)."""
    email = os.environ["ADMIN_EMAIL"]
    password = os.environ["ADMIN_PASSWORD"]
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def fiscal_client(admin_client):
    """Cria usuário fiscal via admin e retorna client autenticado."""
    email = f"fiscal-{uuid.uuid4().hex[:8]}@fiscalcore.local"
    password = "FiscalTest@2026"
    r = admin_client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "Fiscal Test", "role": "fiscal"},
    )
    assert r.status_code == 200, r.text
    with TestClient(app) as c:
        r2 = c.post("/api/auth/login", json={"email": email, "password": password})
        assert r2.status_code == 200
        c.headers.update({"Authorization": f"Bearer {r2.json()['access_token']}"})
        yield c


@pytest.fixture
def auditoria_client(admin_client):
    email = f"audit-{uuid.uuid4().hex[:8]}@fiscalcore.local"
    password = "AuditTest@2026"
    r = admin_client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "Audit Test", "role": "auditoria"},
    )
    assert r.status_code == 200, r.text
    with TestClient(app) as c:
        r2 = c.post("/api/auth/login", json={"email": email, "password": password})
        assert r2.status_code == 200
        c.headers.update({"Authorization": f"Bearer {r2.json()['access_token']}"})
        yield c


REQUEST_GOLDEN = {
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
            "cClassTrib": "000001",
            "quantidade": "1.00",
            "valorUnitario": "1000.00",
            "valorItem": "1000.00",
        },
        {
            "numero": 2,
            "cClassTrib": "200052",
            "quantidade": "1.00",
            "valorUnitario": "500.00",
            "valorItem": "500.00",
        },
        {
            "numero": 3,
            "cClassTrib": "000001",
            "quantidade": "1.00",
            "valorUnitario": "200.00",
            "valorItem": "200.00",
            "impostoSeletivo": {"aliquota": "10.0000", "cst": "01"},
        },
    ],
}
