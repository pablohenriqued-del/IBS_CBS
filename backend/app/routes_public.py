"""Endpoints públicos de download de artefatos (vídeo, carrossel PDF).

Sem autenticação: são artefatos de marketing/portfolio prontos para
compartilhamento externo (LinkedIn, e-mail).
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/public")


_ARTIFACTS = {
    "video": {
        "path": "/app/video/FiscalCore-LinkedIn.mp4",
        "media": "video/mp4",
        "filename": "FiscalCore-LinkedIn.mp4",
    },
    "carrossel": {
        "path": "/app/FiscalCore-LinkedIn-Carousel.pdf",
        "media": "application/pdf",
        "filename": "FiscalCore-LinkedIn-Carousel.pdf",
    },
}


@router.get("/download/{artifact_id}")
async def baixar_artefato(artifact_id: str):
    """Download público de artefatos de portfolio (vídeo LinkedIn + carrossel PDF)."""
    art = _ARTIFACTS.get(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail={"erro": "artefato_nao_encontrado"})
    if not os.path.exists(art["path"]):
        raise HTTPException(status_code=404, detail={"erro": "arquivo_ainda_nao_gerado"})
    return FileResponse(
        art["path"],
        media_type=art["media"],
        filename=art["filename"],
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": f'attachment; filename="{art["filename"]}"',
        },
    )


@router.get("/artefatos")
async def listar_artefatos():
    """Lista artefatos disponíveis para download, com metadados."""
    itens = []
    for aid, meta in _ARTIFACTS.items():
        exists = os.path.exists(meta["path"])
        size = os.path.getsize(meta["path"]) if exists else 0
        itens.append({
            "id": aid,
            "filename": meta["filename"],
            "media_type": meta["media"],
            "disponivel": exists,
            "tamanho_bytes": size,
            "download_url": f"/api/public/download/{aid}",
        })
    return {"artefatos": itens}
