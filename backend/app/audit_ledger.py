"""Trilha de auditoria com hash encadeado (ledger append-only).

Modelo:
  { seq, ts, actor:{id,email,role}|None, action, payload, prev_hash, hash }

Onde hash = sha256(canonical_json({seq, ts, actor, action, payload, prev_hash})).
Uma quebra na cadeia (hash recalculado ≠ hash gravado, ou prev_hash não bate)
é evidência de adulteração.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .db import get_db


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def compute_event_hash(evento: Dict[str, Any]) -> str:
    payload = {k: evento[k] for k in ("seq", "ts", "actor", "action", "payload", "prev_hash")}
    raw = canonical_json(payload).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


async def append_event(
    action: str,
    payload: Dict[str, Any],
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Adiciona um evento à cadeia. Não idempotente por design (ledger).

    Para MVP não usamos lock distribuído; se dois eventos concorrentes
    forem inseridos, o `verificar_integridade` detectará se a cadeia foi
    corrompida (o índice único em `seq` já previne colisão nesse cenário).
    """
    db = get_db()
    last = await db.auditoria_ledger.find_one(sort=[("seq", -1)])
    prev_hash = last["hash"] if last else None
    seq = (last["seq"] + 1) if last else 1
    ts = datetime.now(timezone.utc).isoformat()

    evento = {
        "seq": seq,
        "ts": ts,
        "actor": actor,
        "action": action,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    evento["hash"] = compute_event_hash(evento)
    await db.auditoria_ledger.insert_one(evento)
    return evento


async def listar_eventos(limit: int = 200) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.auditoria_ledger.find({}, {"_id": 0}).sort("seq", -1).limit(limit)
    return [e async for e in cursor]


async def verificar_integridade() -> Dict[str, Any]:
    """Recomputa a cadeia. Retorna:
      { ok: bool, total: int, broken_at: seq|None, motivo: str|None }
    """
    db = get_db()
    cursor = db.auditoria_ledger.find({}, {"_id": 0}).sort("seq", 1)
    prev_hash = None
    total = 0
    async for e in cursor:
        total += 1
        # Recomputa hash com os campos gravados
        expected = compute_event_hash(
            {
                "seq": e["seq"],
                "ts": e["ts"],
                "actor": e.get("actor"),
                "action": e["action"],
                "payload": e.get("payload", {}),
                "prev_hash": e.get("prev_hash"),
            }
        )
        if expected != e["hash"]:
            return {
                "ok": False,
                "total": total,
                "broken_at": e["seq"],
                "motivo": "hash gravado não bate com recomputado (evento adulterado)",
            }
        if e.get("prev_hash") != prev_hash:
            return {
                "ok": False,
                "total": total,
                "broken_at": e["seq"],
                "motivo": "prev_hash não aponta para o hash do evento anterior (cadeia quebrada)",
            }
        prev_hash = e["hash"]
    return {"ok": True, "total": total, "broken_at": None, "motivo": None}
