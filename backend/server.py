"""FiscalCore Motor — FastAPI entrypoint."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.db import seed_rulesets  # noqa: E402
from app.routes import router  # noqa: E402
from app.rulesets import RULESETS_SEED, compute_ruleset_hash  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO(auth): implementar API keys por tenant antes de produção
    await seed_rulesets(RULESETS_SEED, compute_ruleset_hash)
    yield


app = FastAPI(
    title="FiscalCore Motor",
    version="0.1.0",
    description="API determinística e auditável de cálculo de IBS/CBS (Reforma Tributária 2026).",
    lifespan=lifespan,
)

cors_origins = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")] if cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def raiz():
    return {
        "servico": "fiscalcore-motor",
        "versao": "0.1.0",
        "endpoints": [
            "GET  /api/v1/health",
            "GET  /api/v1/rulesets",
            "POST /api/v1/calcular",
            "GET  /api/v1/auditoria/{id}",
        ],
    }
