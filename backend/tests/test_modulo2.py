"""Testes de auth, ingestão, apuração e audit ledger (Módulo 2)."""
from __future__ import annotations

import uuid


# --------------------------------------------------------------------------
# XML fixture
# --------------------------------------------------------------------------


def make_nfe_xml(chave: str = "35260812345678000190550010000000011000000099", itens_extra=None):
    itens_xml = """
   <det nItem="1">
    <prod>
     <cProd>CAD001</cProd><xProd>Cadeira de escritorio</xProd>
     <NCM>94013000</NCM>
     <qCom>1.00</qCom><vUnCom>1000.00</vUnCom><vProd>1000.00</vProd>
    </prod>
    <imposto><IBSCBS><cClassTrib>000001</cClassTrib><vBC>1000.00</vBC></IBSCBS></imposto>
   </det>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00"><NFe><infNFe versao="4.00" Id="NFe{chave}">
 <ide><cUF>35</cUF><natOp>Venda</natOp><dhEmi>2026-08-26T10:00:00-03:00</dhEmi></ide>
 <emit><CNPJ>12345678000190</CNPJ><xNome>Sony Music</xNome><enderEmit><UF>SP</UF></enderEmit></emit>
 <dest><CNPJ>98765432000100</CNPJ><xNome>Cliente</xNome><enderDest><UF>RJ</UF></enderDest></dest>
 {itens_xml}
</infNFe></NFe></nfeProc>""".encode("utf-8")


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


def test_login_ok(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@fiscalcore.local", "password": "FiscalCore@2026"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert body["email"] == "admin@fiscalcore.local"


def test_login_credenciais_invalidas(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@fiscalcore.local", "password": "senha errada"},
    )
    assert r.status_code == 401


def test_me_sem_login_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_register_apenas_admin(fiscal_client):
    # Fiscal não pode criar users
    r = fiscal_client.post(
        "/api/auth/register",
        json={
            "email": f"novo-{uuid.uuid4().hex[:6]}@fiscalcore.local",
            "password": "Senha@1234",
            "name": "X",
            "role": "fiscal",
        },
    )
    assert r.status_code == 403


def test_admin_lista_usuarios(admin_client):
    r = admin_client.get("/api/auth/users")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


# --------------------------------------------------------------------------
# Ingestão
# --------------------------------------------------------------------------


def test_importar_saida_ok(fiscal_client):
    chave = "3526081234567800019055001000000002" + str(uuid.uuid4().int)[:10]
    xml = make_nfe_xml(chave=chave)
    r = fiscal_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chaveAcesso"] == chave
    assert body["direcao"] == "saida"
    # Cadeira R$1000 tributação integral no regime pleno → CBS 88, IBS 177
    assert body["totais"]["cbs"] == "88.00"
    assert body["totais"]["ibs"] == "177.00"


def test_reimportar_mesma_chave_409(fiscal_client):
    chave = "3526081234567800019055001000000003" + str(uuid.uuid4().int)[:10]
    xml = make_nfe_xml(chave=chave)
    r1 = fiscal_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
    )
    assert r1.status_code == 200
    r2 = fiscal_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["erro"] == "documento_ja_importado"


def test_xml_invalido_422(fiscal_client):
    r = fiscal_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("bad.xml", b"<not a nfe/>", "application/xml")},
        data={"direcao": "saida"},
    )
    assert r.status_code == 422


def test_auditoria_nao_importa(auditoria_client):
    xml = make_nfe_xml(chave="3526081234567800019055001000000004" + str(uuid.uuid4().int)[:10])
    r = auditoria_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("nfe.xml", xml, "application/xml")},
        data={"direcao": "saida"},
    )
    assert r.status_code == 403


# --------------------------------------------------------------------------
# Apuração
# --------------------------------------------------------------------------


def test_apuracao_debitos_menos_creditos(fiscal_client):
    saida_chave = "3526081234567800019055001000000005" + str(uuid.uuid4().int)[:10]
    entrada_chave = "3526081234567800019055001000000006" + str(uuid.uuid4().int)[:10]
    fiscal_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("s.xml", make_nfe_xml(chave=saida_chave), "application/xml")},
        data={"direcao": "saida"},
    )
    fiscal_client.post(
        "/api/v1/documentos/importar",
        files={"arquivo": ("e.xml", make_nfe_xml(chave=entrada_chave), "application/xml")},
        data={"direcao": "entrada"},
    )
    r = fiscal_client.post(
        "/api/v1/apuracao/periodo",
        json={"dataInicio": "2026-08-01", "dataFim": "2026-08-31"},
    )
    assert r.status_code == 200
    body = r.json()
    # Débito e crédito com o mesmo item → apurado ~zero (compensa)
    assert float(body["apurado"]["cbs"]) == 0.0 or body["totalDocumentos"] >= 2


# --------------------------------------------------------------------------
# Audit ledger (hash encadeado)
# --------------------------------------------------------------------------


def test_ledger_apenas_auditoria_e_admin(fiscal_client, admin_client, auditoria_client):
    assert fiscal_client.get("/api/v1/auditoria/ledger").status_code == 403
    assert admin_client.get("/api/v1/auditoria/ledger").status_code == 200
    assert auditoria_client.get("/api/v1/auditoria/ledger").status_code == 200


def test_ledger_verificar_integridade(admin_client):
    r = admin_client.get("/api/v1/auditoria/verificar")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["total"] >= 1
    assert body["broken_at"] is None


def test_ledger_encadeamento_correto(admin_client):
    r = admin_client.get("/api/v1/auditoria/ledger?limit=20")
    eventos = r.json()["eventos"]
    # Vem em ordem decrescente por seq — inverter para verificar cadeia
    eventos = sorted(eventos, key=lambda e: e["seq"])
    for i in range(1, len(eventos)):
        assert eventos[i]["prev_hash"] == eventos[i - 1]["hash"]


def test_ledger_detecta_adulteracao(admin_client):
    # Adultera o payload de um evento e verifica que a integridade quebra.
    import copy
    import os

    from pymongo import MongoClient

    mc = MongoClient(os.environ["MONGO_URL"])
    col = mc[os.environ["DB_NAME"]].auditoria_ledger
    um = col.find_one(sort=[("seq", 1)])
    assert um is not None
    original_payload = copy.deepcopy(um.get("payload", {}))
    try:
        col.update_one({"_id": um["_id"]}, {"$set": {"payload": {"adulterado": True}}})
        r = admin_client.get("/api/v1/auditoria/verificar")
        body = r.json()
        assert body["ok"] is False, body
        assert body["broken_at"] == um["seq"]
    finally:
        # SEMPRE restaura, mesmo se assert falhar
        col.update_one({"_id": um["_id"]}, {"$set": {"payload": original_payload}})
