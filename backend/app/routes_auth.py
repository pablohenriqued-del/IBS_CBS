"""Rotas de autenticação (login, register, me, logout, refresh)."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .audit_ledger import append_event
from .auth import (
    LoginRequest,
    RegisterRequest,
    _clear_auth_cookies,
    _set_auth_cookies,
    check_lockout,
    clear_login_attempts,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    register_failed_login,
    require_role,
    verify_password,
)
from .db import get_db

router = APIRouter(prefix="/api/auth")


def _user_public(user: dict) -> dict:
    uid = user.get("_id") or user.get("id")
    return {
        "id": str(uid),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"

    await check_lockout(identifier)

    db = get_db()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        await register_failed_login(identifier)
        raise HTTPException(status_code=401, detail="credenciais inválidas")

    await clear_login_attempts(identifier)

    uid = str(user["_id"])
    access = create_access_token(uid, email, user["role"])
    refresh = create_refresh_token(uid)
    _set_auth_cookies(response, access, refresh)

    await append_event(
        action="auth.login",
        payload={"email": email},
        actor={"id": uid, "email": email, "role": user["role"]},
    )
    return {**_user_public(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    _clear_auth_cookies(response)
    await append_event(
        action="auth.logout",
        payload={"email": user["email"]},
        actor={"id": user["id"], "email": user["email"], "role": user["role"]},
    )
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return _user_public(user)


@router.post("/register")
async def register(
    payload: RegisterRequest,
    admin: dict = Depends(require_role("admin")),
):
    db = get_db()
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="e-mail já cadastrado")
    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name,
        "role": payload.role,
        "created_at": datetime.now(timezone.utc),
        "created_by": admin["id"],
    }
    result = await db.users.insert_one(doc)
    await append_event(
        action="auth.register",
        payload={"email": email, "role": payload.role},
        actor={"id": admin["id"], "email": admin["email"], "role": admin["role"]},
    )
    return {"id": str(result.inserted_id), "email": email, "name": payload.name, "role": payload.role}


@router.get("/users")
async def listar_usuarios(admin: dict = Depends(require_role("admin"))):
    db = get_db()
    cursor = db.users.find({}, {"password_hash": 0}).sort("created_at", 1)
    users = []
    async for u in cursor:
        u["id"] = str(u.pop("_id"))
        u["created_at"] = str(u.get("created_at", ""))
        users.append(u)
    return {"users": users, "total": len(users)}
