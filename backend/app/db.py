"""Camada de acesso a MongoDB (append-only para auditoria)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def get_db() -> AsyncIOMotorDatabase:
    """Cria client novo por chamada — evita `Event loop is closed` no TestClient
    (cada teste tem um loop novo). Em produção com uvicorn, o custo é
    desprezível pois pymongo mantém pool interno.
    """
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


async def seed_rulesets(rulesets_seed: List[Dict[str, Any]], hasher) -> None:
    """Faz upsert idempotente dos rulesets iniciais (por id + hash).

    - Coleção `rulesets` é logicamente append-only: nunca sobrescrevemos
      artefatos com o mesmo (id, hash). Se o hash mudou para o mesmo id,
      inserimos uma nova revisão (mas o id normalmente já incluiria a versão).
    """
    db = get_db()
    for r in rulesets_seed:
        h = hasher(r)
        existing = await db.rulesets.find_one({"id": r["id"], "hash": h})
        if not existing:
            doc = dict(r)
            doc["hash"] = h
            await db.rulesets.insert_one(doc)


async def carregar_rulesets() -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.rulesets.find({}, {"_id": 0})
    return [r async for r in cursor]


async def gravar_auditoria(registro: Dict[str, Any]) -> str:
    """Append-only: grava snapshot completo (input + ruleset_id + hash + output)."""
    db = get_db()
    result = await db.auditoria.insert_one(registro)
    return str(result.inserted_id)


async def get_auditoria(auditoria_id: str) -> Optional[Dict[str, Any]]:
    from bson import ObjectId

    db = get_db()
    try:
        oid = ObjectId(auditoria_id)
    except Exception:
        return None
    doc = await db.auditoria.find_one({"_id": oid})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc
