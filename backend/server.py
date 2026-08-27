"""FiscalCore Motor — FastAPI entrypoint."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.audit_ledger import append_event  # noqa: E402
from app.auth import ensure_indexes, seed_admin  # noqa: E402
from app.db import seed_rulesets  # noqa: E402
from app.routes import router as router_motor  # noqa: E402
from app.routes_auth import router as router_auth  # noqa: E402
from app.routes_docs import router as router_docs  # noqa: E402
from app.routes_public import router as router_public  # noqa: E402
from app.routes_sap import router as router_sap  # noqa: E402
from app.rulesets import RULESETS_SEED, compute_ruleset_hash  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_rulesets(RULESETS_SEED, compute_ruleset_hash)
    await seed_admin()
    # Ledger: registra apenas 1 evento de bootstrap por processo
    try:
        await append_event(
            action="sistema.startup",
            payload={"motorVersao": os.environ.get("MOTOR_VERSAO", "dev")},
            actor=None,
        )
    except Exception:
        pass
    yield


app = FastAPI(
    title="FiscalCore Motor",
    version="0.2.0",
    description="API determinística e auditável de cálculo de IBS/CBS (Reforma Tributária 2026).",
    lifespan=lifespan,
)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
origins = [frontend_url]
# Também aceita * em desenvolvimento local sem credenciais
cors_origins_env = os.environ.get("CORS_ORIGINS", "").strip()
if cors_origins_env and cors_origins_env != "*":
    origins.extend([o.strip() for o in cors_origins_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_auth)
app.include_router(router_motor)
app.include_router(router_docs)
app.include_router(router_sap)
app.include_router(router_public)


@app.get("/")
async def raiz():
    return {
        "servico": "fiscalcore-motor",
        "versao": "0.2.0",
        "modulos": ["motor", "auth", "documentos", "apuracao", "auditoria-ledger"],
        "endpoints": [
            "POST /api/auth/login",
            "POST /api/auth/logout",
            "GET  /api/auth/me",
            "POST /api/auth/register (admin)",
            "GET  /api/auth/users (admin)",
            "GET  /api/v1/health",
            "GET  /api/v1/rulesets",
            "POST /api/v1/calcular (fiscal, admin)",
            "GET  /api/v1/auditoria/{id} (any authenticated)",
            "POST /api/v1/documentos/importar (fiscal, admin)",
            "GET  /api/v1/documentos",
            "GET  /api/v1/documentos/{id}",
            "POST /api/v1/apuracao/periodo",
            "GET  /api/v1/auditoria/ledger (auditoria, admin)",
            "GET  /api/v1/auditoria/verificar (auditoria, admin)",
            "POST /api/v1/sap/pricing (fiscal, admin)",
            "GET  /api/v1/sap/exemplo",
        ],
    }
