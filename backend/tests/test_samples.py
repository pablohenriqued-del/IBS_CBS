"""External tests for the samples endpoints (list + download) and their
integration with the existing /api/v1/documentos/importar flow."""
from __future__ import annotations

import os

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://tributaria-core.preview.emergentagent.com",
).rstrip("/")
ADMIN_EMAIL = "admin@fiscalcore.local"
ADMIN_PASSWORD = "FiscalCore@2026"

EXPECTED_SAMPLES = [
    "01-cadeira-integral.xml",
    "02-medicamento-reducao60.xml",
    "03-bebida-imposto-seletivo.xml",
    "04-nota-completa-3-itens.xml",
    "05-entrada-fornecedor.xml",
    "06-fase-teste-2026.xml",
]


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# -- Listagem ------------------------------------------------------------

def test_list_samples_requires_auth():
    r = requests.get(f"{BASE_URL}/api/v1/samples", timeout=10)
    assert r.status_code in (401, 403), r.text


def test_list_samples_returns_six(admin_headers):
    r = requests.get(f"{BASE_URL}/api/v1/samples", headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 6
    amostras = body["amostras"]
    assert len(amostras) == 6
    required_keys = {"arquivo", "titulo", "resumo", "direcao", "dataOperacao", "ruleset"}
    for a in amostras:
        assert required_keys.issubset(a.keys()), f"missing keys in {a}"
    arquivos = {a["arquivo"] for a in amostras}
    assert arquivos == set(EXPECTED_SAMPLES)


# -- Download individual --------------------------------------------------

@pytest.mark.parametrize("nome", EXPECTED_SAMPLES)
def test_download_each_sample(admin_headers, nome):
    r = requests.get(f"{BASE_URL}/api/v1/samples/{nome}", headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    assert "xml" in r.headers.get("content-type", "").lower()
    body = r.text
    assert body.lstrip().startswith("<?xml"), body[:80]


def test_download_first_sample_contents(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/v1/samples/01-cadeira-integral.xml",
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/xml")
    text = r.text
    assert text.lstrip().startswith("<?xml")
    assert "nfeProc" in text
    assert "NFe" in text
    assert "CAD001" in text


# -- Segurança (path traversal / extensão) --------------------------------

def test_path_traversal_blocked_dotdot(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/v1/samples/../server.py",
        headers=admin_headers,
        timeout=10,
        allow_redirects=False,
    )
    assert r.status_code in (400, 404), r.text
    assert "def " not in r.text  # não vaza o server.py


def test_path_traversal_blocked_encoded(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/v1/samples/..%2Fserver.py",
        headers=admin_headers,
        timeout=10,
        allow_redirects=False,
    )
    assert r.status_code in (400, 404), r.text
    assert "def " not in r.text


def test_non_xml_blocked(admin_headers):
    r = requests.get(f"{BASE_URL}/api/v1/samples/hack.py", headers=admin_headers, timeout=10)
    assert r.status_code == 400, r.text


def test_missing_sample_returns_404(admin_headers):
    r = requests.get(
        f"{BASE_URL}/api/v1/samples/99-nao-existe.xml",
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 404, r.text


# -- Importação das amostras (integração com ingestão) --------------------

def _import(admin_headers, nome, direcao):
    dl = requests.get(f"{BASE_URL}/api/v1/samples/{nome}", headers=admin_headers, timeout=10)
    assert dl.status_code == 200
    files = {"arquivo": (nome, dl.content, "application/xml")}
    data = {"direcao": direcao}
    return requests.post(
        f"{BASE_URL}/api/v1/documentos/importar",
        headers=admin_headers,
        files=files,
        data=data,
        timeout=20,
    )


def test_import_04_nota_completa_golden(admin_headers):
    """Golden case: 3 itens = tributosTotais 376.30. Aceita 200 (fresh) OU 409 (already imported)."""
    r = _import(admin_headers, "04-nota-completa-3-itens.xml", "saida")
    if r.status_code == 200:
        doc = r.json()
        assert doc["totais"]["tributosTotais"] == "376.30", doc["totais"]
        assert doc["chaveAcesso"].endswith("000000404")
    elif r.status_code == 409:
        detail = r.json().get("detail", {})
        assert detail.get("erro") == "documento_ja_importado"
        assert detail.get("chaveAcesso", "").endswith("000000404")
    else:
        pytest.fail(f"unexpected status {r.status_code}: {r.text}")


def test_import_06_fase_teste_ruleset(admin_headers):
    r = _import(admin_headers, "06-fase-teste-2026.xml", "saida")
    if r.status_code == 200:
        doc = r.json()
        assert doc["totais"]["cbs"] == "9.00", doc["totais"]
        assert doc["totais"]["ibs"] == "1.00", doc["totais"]
        assert "fase-teste" in doc.get("rulesetId", "").lower() or \
               doc.get("rulesetId") == "ruleset:2026-fase-teste"
    elif r.status_code == 409:
        pass  # ok — já importado
    else:
        pytest.fail(f"unexpected status {r.status_code}: {r.text}")


def test_import_03_imposto_seletivo_na_base(admin_headers):
    r = _import(admin_headers, "03-bebida-imposto-seletivo.xml", "saida")
    if r.status_code == 200:
        doc = r.json()
        assert doc["totais"]["impostoSeletivo"] == "20.00", doc["totais"]
        # Verifica que IS entra na base do item
        item = doc["itens"][0] if doc.get("itens") else None
        if item is not None:
            assert item.get("base") == "220.00", item
    elif r.status_code == 409:
        pass
    else:
        pytest.fail(f"unexpected status {r.status_code}: {r.text}")


def test_import_04_idempotency(admin_headers):
    """Importar a mesma amostra duas vezes → segunda deve retornar 409."""
    _import(admin_headers, "04-nota-completa-3-itens.xml", "saida")
    r2 = _import(admin_headers, "04-nota-completa-3-itens.xml", "saida")
    assert r2.status_code == 409, r2.text
    detail = r2.json().get("detail", {})
    assert detail.get("erro") == "documento_ja_importado"


# -- Regressão spot-check golden calc -------------------------------------

def test_regression_golden_calc(admin_headers):
    payload = {
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
    r = requests.post(
        f"{BASE_URL}/api/v1/calcular",
        json=payload,
        headers=admin_headers,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    totais = r.json()["totais"]
    assert totais["baseTotal"] == "1720.00", totais
    assert totais["cbs"] == "124.96", totais
    assert totais["ibs"] == "251.34", totais
    assert totais["tributosTotais"] == "376.30", totais
