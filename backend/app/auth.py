"""Autenticação por JWT + bcrypt + papéis (fiscal / auditoria / admin).

Playbook aplicado: httpOnly cookies com fallback Bearer, brute-force lockout,
seed idempotente do admin, indexes únicos.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from bson import ObjectId
from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from .db import get_db

ROLES = {"fiscal", "auditoria", "admin"}
JWT_ALGO = "HS256"
ACCESS_TTL_MIN = 60 * 8  # 8h (uso interno)
REFRESH_TTL_DAYS = 7
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCK_MINUTES = 15


def _secret() -> str:
    return os.environ["JWT_SECRET"]


# --------------------------------------------------------------------------
# Hash
# --------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGO)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGO)


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    common = {"httponly": True, "secure": True, "samesite": "none", "path": "/"}
    response.set_cookie("access_token", access, max_age=ACCESS_TTL_MIN * 60, **common)
    response.set_cookie("refresh_token", refresh, max_age=REFRESH_TTL_DAYS * 86400, **common)


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# --------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="não autenticado")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="token inválido")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="tipo de token inválido")

    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        raise HTTPException(status_code=401, detail="usuário inválido")
    if not user:
        raise HTTPException(status_code=401, detail="usuário não encontrado")
    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    return user


def require_role(*allowed_roles: str):
    async def _dep(request: Request) -> dict:
        user = await get_current_user(request)
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"acesso restrito a: {', '.join(allowed_roles)}")
        return user

    return _dep


# --------------------------------------------------------------------------
# Brute-force lockout
# --------------------------------------------------------------------------


async def check_lockout(identifier: str) -> None:
    db = get_db()
    doc = await db.login_attempts.find_one({"identifier": identifier})
    if not doc:
        return
    if doc.get("count", 0) >= LOGIN_MAX_ATTEMPTS:
        locked_until = doc.get("locked_until")
        if locked_until and locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=429,
                detail=f"muitas tentativas — bloqueado até {locked_until.isoformat()}",
            )


async def register_failed_login(identifier: str) -> None:
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = await db.login_attempts.find_one({"identifier": identifier})
    count = (doc.get("count", 0) if doc else 0) + 1
    update = {"count": count, "last_attempt": now}
    if count >= LOGIN_MAX_ATTEMPTS:
        update["locked_until"] = now + timedelta(minutes=LOGIN_LOCK_MINUTES)
    await db.login_attempts.update_one(
        {"identifier": identifier}, {"$set": update}, upsert=True
    )


async def clear_login_attempts(identifier: str) -> None:
    db = get_db()
    await db.login_attempts.delete_one({"identifier": identifier})


# --------------------------------------------------------------------------
# Seed admin idempotente
# --------------------------------------------------------------------------


async def seed_admin() -> None:
    db = get_db()
    email = os.environ["ADMIN_EMAIL"].strip().lower()
    password = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": email})
    now = datetime.now(timezone.utc)
    if existing is None:
        await db.users.insert_one(
            {
                "email": email,
                "password_hash": hash_password(password),
                "name": "Admin",
                "role": "admin",
                "created_at": now,
            }
        )
    elif not verify_password(password, existing["password_hash"]):
        # Rehash if env password changed
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": hash_password(password), "updated_at": now}},
        )


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.documentos.create_index("chaveAcesso", unique=True)
    await db.documentos.create_index([("dataEmissao", 1)])
    await db.auditoria_ledger.create_index([("seq", 1)], unique=True)


# --------------------------------------------------------------------------
# Pydantic schemas
# --------------------------------------------------------------------------


import re

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    role: str = Field(pattern="^(fiscal|auditoria|admin)$")

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("e-mail inválido")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("e-mail inválido")
        return v


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
