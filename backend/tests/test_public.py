"""Testes dos endpoints públicos: contato, stats, rate limit, download."""
from __future__ import annotations

from app.routes_public import demo_reset_all


def setup_function():
    """Reseta o rate limiter em memória entre testes."""
    demo_reset_all()


# --- Contato ----------------------------------------------------------------


def test_contato_valida_email(client):
    r = client.post("/api/public/contato", json={"nome": "OK", "email": "invalido", "mensagem": "teste"})
    assert r.status_code == 422


def test_contato_valida_nome_min(client):
    r = client.post("/api/public/contato", json={"nome": "A", "email": "a@b.com", "mensagem": "teste"})
    assert r.status_code == 422


def test_contato_valida_mensagem_min(client):
    r = client.post("/api/public/contato", json={"nome": "Fulano", "email": "a@b.com", "mensagem": "no"})
    assert r.status_code == 422


def test_contato_criacao_ok(client):
    r = client.post(
        "/api/public/contato",
        json={
            "nome": "Ana Teste",
            "email": "ana@teste.com",
            "empresa": "ACME",
            "mensagem": "Interessada em conversar sobre integração SAP.",
            "origem": "sobre",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert "id" in body


def test_contato_grava_evento_ledger(admin_client):
    from fastapi.testclient import TestClient
    from server import app
    with TestClient(app) as anon:
        anon.post(
            "/api/public/contato",
            json={"nome": "Bia", "email": "bia@teste.com", "mensagem": "quero conversar"},
        )
    r = admin_client.get("/api/v1/auditoria/ledger?limit=5")
    eventos = r.json()["eventos"]
    assert any(e["action"] == "contato.novo" for e in eventos)


def test_contato_lista_admin_only(admin_client):
    from fastapi.testclient import TestClient
    from server import app
    # Cria um lead via cliente anônimo separado (novo TestClient sem auth)
    with TestClient(app) as anon:
        anon.post("/api/public/contato", json={
            "nome": "Carlos", "email": "carlos@teste.com", "mensagem": "consulta ok",
        })
        # Sem auth: 401
        r_anon = anon.get("/api/public/contato/lista")
        assert r_anon.status_code == 401
    # Admin: 200
    r_adm = admin_client.get("/api/public/contato/lista")
    assert r_adm.status_code == 200
    assert r_adm.json()["total"] >= 1


# --- Stats ------------------------------------------------------------------


def test_stats_publico(client):
    r = client.get("/api/public/stats")
    assert r.status_code == 200
    body = r.json()
    for k in ("calculos_totais", "calculos_demo", "documentos_importados"):
        assert k in body
        assert isinstance(body[k], int)


def test_stats_demo_incrementa(client):
    stats_antes = client.get("/api/public/stats").json()
    client.post("/api/v1/calcular", json={
        "referencia": "stats-test",
        "dataOperacao": "2026-08-26",
        "modo": "producao",
        "estabelecimento": {"cnpj": "12345678000190", "uf": "SP", "municipioIBGE": "3550308", "regime": "regular"},
        "destinatario": {"uf": "RJ", "municipioIBGE": "3304557", "consumidorFinal": True, "contribuinte": False},
        "operacao": {"tipo": "venda"},
        "itens": [{"numero": 1, "cClassTrib": "000001", "quantidade": "1", "valorUnitario": "100", "valorItem": "100"}],
    })
    stats_dep = client.get("/api/public/stats").json()
    assert stats_dep["calculos_demo"] >= stats_antes["calculos_demo"] + 1


# --- Rate limit (10/hora por IP) --------------------------------------------


def _payload_min():
    return {
        "referencia": "rl", "dataOperacao": "2026-08-26", "modo": "producao",
        "estabelecimento": {"cnpj": "12345678000190", "uf": "SP", "municipioIBGE": "3550308", "regime": "regular"},
        "destinatario": {"uf": "RJ", "municipioIBGE": "3304557", "consumidorFinal": True, "contribuinte": False},
        "operacao": {"tipo": "venda"},
        "itens": [{"numero": 1, "cClassTrib": "000001", "quantidade": "1", "valorUnitario": "100", "valorItem": "100"}],
    }


def test_rate_limit_demo_11a_call_retorna_429(client):
    p = _payload_min()
    for i in range(10):
        r = client.post("/api/v1/calcular", json=p)
        assert r.status_code == 200, f"call #{i+1} falhou: {r.text}"
    r11 = client.post("/api/v1/calcular", json=p)
    assert r11.status_code == 429
    detail = r11.json()["detail"]
    assert detail["erro"] == "rate_limit_demo"
    assert detail["retryAfterSeconds"] > 0
    # Header Retry-After presente
    assert "retry-after" in {k.lower() for k in r11.headers.keys()}


def test_rate_limit_nao_afeta_autenticado(admin_client, client):
    # Consome os 10 do IP anônimo
    p = _payload_min()
    for _ in range(10):
        client.post("/api/v1/calcular", json=p)
    # Admin com token continua funcionando (sem limite demo)
    r = admin_client.post("/api/v1/calcular", json=p)
    assert r.status_code == 200


# --- Download ---------------------------------------------------------------


def test_artefatos_lista(client):
    r = client.get("/api/public/artefatos")
    assert r.status_code == 200
    ids = {a["id"] for a in r.json()["artefatos"]}
    assert {"video", "trailer", "carrossel"}.issubset(ids)


def test_download_artefato_inexistente_404(client):
    r = client.get("/api/public/download/naoexiste")
    assert r.status_code == 404
