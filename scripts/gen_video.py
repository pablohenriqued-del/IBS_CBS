"""FiscalCore — Gerador de vídeo explicativo para LinkedIn.

Pipeline:
  1. Fase 1: Gera narração TTS por cena (OpenAI 'onyx', PT-BR).
  2. Fase 2: Para cada cena, roda Playwright ao vivo gravando WebM 1920x1080.
     A duração da gravação = duração exata do áudio + buffer.
  3. Fase 3: Para cada cena, ffmpeg combina video + audio + overlay de legenda
     cinematográfica (Fraunces bold em fundo escurecido). Concatena tudo.

Saída final: /app/video/FiscalCore-LinkedIn.mp4  (1920x1080, ~120s, MP4/H264/AAC)
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.openai import OpenAITextToSpeech  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

BASE = "https://tributaria-core.preview.emergentagent.com"
EMAIL = "admin@fiscalcore.local"
PASSWORD = "FiscalCore@2026"

OUT = Path("/app/video")
AUDIO_DIR = OUT / "audio"
RAW_DIR = OUT / "raw"
SCENE_DIR = OUT / "scenes"
FINAL = OUT / "FiscalCore-LinkedIn.mp4"
FONT_BOLD = "/app/video/fonts/Fraunces-Bold.ttf"
FONT_ITALIC = "/app/video/fonts/Fraunces-BoldItalic.ttf"

for d in (AUDIO_DIR, RAW_DIR, SCENE_DIR):
    d.mkdir(parents=True, exist_ok=True)

CHROMIUM = "/pw-browsers/chromium_headless_shell-1208/chrome-linux/headless_shell"
FFMPEG = "ffmpeg"


# ---------------------------------------------------------------------------
# Roteiro (PT-BR). Duração final ~120s.
# ---------------------------------------------------------------------------
SCENES: List[Dict[str, Any]] = [
    {
        "id": "01_hook",
        "narracao": (
            "Toda empresa que emite nota fiscal vai precisar recalcular o passado. "
            "A Reforma Tributária cria três regimes convivendo até dois mil e trinta e três. "
            "Isso não é problema de alíquota. É problema de arquitetura."
        ),
        "caption_top": "O problema",
        "caption_main": "A regra da nota emitida em julho é a regra de julho.",
        "caption_sub": "Hoje, amanhã ou numa fiscalização em 2031.",
        "route": "/sobre",  # Página pública, hero com contexto
        "scroll_y": 0,
        "action": None,
        "video_skip": 4.5,
    },
    {
        "id": "02_playground",
        "narracao": (
            "O motor FiscalCore calcula IBS e CBS em Decimal puro — jamais float. "
            "Base por fora. Imposto Seletivo compondo a base. "
            "Cadeira, medicamento e bebida: trezentos e setenta e seis reais e trinta centavos. Byte a byte."
        ),
        "caption_top": "Playground · POST /v1/calcular",
        "caption_main": "Os três casos-ouro, ao vivo.",
        "caption_sub": "Decimal · base por fora · IS na base · memória de cálculo linha a linha",
        "route": "/",
        "scroll_y": 1400,
        "action": "calcular",
        "wait_after_action": 3.0,
        "video_skip": 5.5,
    },
    {
        "id": "03_simulador",
        "narracao": (
            "O simulador comparativo mostra: regime atual, trezentos e setenta e sete reais. "
            "Reforma, trezentos e noventa e seis e trinta. "
            "Delta positivo de dezenove reais e trinta centavos por operação. "
            "Multiplicado por milhões de notas, isso vira estratégia."
        ),
        "caption_top": "Simulador · Atual vs Reforma",
        "caption_main": "Quanto vai mudar?",
        "caption_sub": "Delta em reais e em percentual — pronto para modelagem de impacto financeiro.",
        "route": "/simulador",
        "scroll_y": 0,
        "action": "simular",
        "wait_after_action": 2.5,
        "video_skip": 5.0,
    },
    {
        "id": "04_auditoria",
        "narracao": (
            "Cada cálculo grava um evento no ledger imutável com hash SHA duzentos e cinquenta e seis encadeado. "
            "Se alguém adulterar um registro, a cadeia quebra. "
            "O verificador aponta o exato ponto da ruptura. Evidência forense reproduzível."
        ),
        "caption_top": "Auditoria · GET /v1/auditoria/verificar",
        "caption_main": "Trilha imutável.",
        "caption_sub": "Hash SHA-256 encadeado. Adulteração quebra a cadeia — e aponta o seq exato.",
        "route": "/auditoria",
        "scroll_y": 0,
        "action": None,
        "wait_after_action": 1.0,
        "video_skip": 4.0,
    },
    {
        "id": "05_sap_komv",
        "narracao": (
            "O motor conversa com o S quatro HANA no formato KOMV nativo. "
            "Condition types Z-namespace: CBS, IBS UF, IBS Município, Imposto Seletivo. "
            "Zero A B A P crítico. O motor é autoritativo."
        ),
        "caption_top": "SAP S/4HANA · POST /v1/sap/pricing",
        "caption_main": "Motor externo autoritativo.",
        "caption_sub": "Payload KOMV nativo. ZCBS, ZIBU, ZIBM, ZISE nos STUNR corretos do pricing schema.",
        "route": "/",
        "scroll_y": 1400,
        "action": "sap_modal",
        "wait_after_action": 2.5,
        "video_skip": 5.5,
    },
    {
        "id": "06_sap_reconciliar",
        "narracao": (
            "Recebe um IDOC INVOIC zero dois do SAP. Recalcula tudo. "
            "E aponta, condição por condição, onde SAP e FiscalCore divergem. "
            "Aqui: quatro erros do ERP detectados automaticamente. Delta em reais."
        ),
        "caption_top": "Reconciliação · SAP vs FiscalCore",
        "caption_main": "Onde o ERP errou — e por quantos centavos.",
        "caption_sub": "IDOC parseado, motor recalculado, veredicto por (KPOSN, KSCHL) com delta em R$.",
        "route": "/sap",
        "scroll_y": 0,
        "action": "reconciliar_diverge",
        "wait_after_action": 3.0,
        "video_skip": 5.5,
    },
    {
        "id": "07_assinatura",
        "narracao": (
            "Feito com disciplina de engenharia. "
            "Decimal. Base por fora. Regras versionadas. Trilha imutável. "
            "FiscalCore Motor. Por Pablo Duarte. Gerente de Inovação e TI."
        ),
        "caption_top": "FiscalCore Motor · v0.2.0",
        "caption_main": "Pablo Duarte — Gerente de Inovação e TI",
        "caption_sub": "linkedin.com/in/pablo-henrique-duarte",
        "route": "/sobre",
        "scroll_y": 800,
        "action": None,
        "wait_after_action": 1.0,
        "video_skip": 4.0,
    },
]


# ---------------------------------------------------------------------------
# Fase 1: TTS
# ---------------------------------------------------------------------------


async def gerar_tts():
    api_key = os.environ["EMERGENT_LLM_KEY"]
    tts = OpenAITextToSpeech(api_key=api_key)
    for scene in SCENES:
        path = AUDIO_DIR / f"{scene['id']}.mp3"
        if path.exists():
            print(f"  cache TTS {scene['id']}")
            continue
        print(f"  gerando TTS {scene['id']}...")
        audio = await tts.generate_speech(
            text=scene["narracao"],
            model="tts-1-hd",
            voice="onyx",  # deep, authoritative — C-level tone
            speed=1.0,
            response_format="mp3",
        )
        path.write_bytes(audio)


def duracao_audio(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True, capture_output=True, text=True,
    )
    return float(r.stdout.strip())


# ---------------------------------------------------------------------------
# Fase 2: Recording com Playwright
# ---------------------------------------------------------------------------


async def _login(page):
    await page.goto(f"{BASE}/login", wait_until="networkidle")
    await page.fill('[data-testid="login-email"]', EMAIL)
    await page.fill('[data-testid="login-password"]', PASSWORD)
    await page.click('[data-testid="login-submit"]')
    await page.wait_for_url(f"{BASE}/", timeout=15000)
    await asyncio.sleep(1)


async def _executar_acao(page, action: str):
    if action == "calcular":
        try:
            await page.click('[data-testid="calcular-btn"]', timeout=5000)
        except Exception:
            pass
    elif action == "simular":
        # try both testids possible
        for sel in ['[data-testid="simular-btn"]', 'button:has-text("Simular")', 'button:has-text("Comparar")']:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    break
            except Exception:
                continue
    elif action == "sap_modal":
        try:
            await page.click('[data-testid="sap-simular-btn"]', timeout=5000)
            await page.wait_for_selector('[data-testid="sap-komv-table"]', timeout=10000)
        except Exception:
            pass
    elif action == "reconciliar_diverge":
        try:
            await page.click('[data-testid="load-sample-diverge"]', timeout=5000)
            await page.wait_for_selector('[data-testid="sap-rec-veredicto"]', timeout=15000)
        except Exception:
            pass


async def gravar_cenas():
    async with async_playwright() as p:
        for scene in SCENES:
            audio_path = AUDIO_DIR / f"{scene['id']}.mp3"
            dur = duracao_audio(audio_path)
            record_dur = dur + 1.0  # buffer

            raw_dir = RAW_DIR / scene["id"]
            raw_dir.mkdir(exist_ok=True)
            # limpa gravações antigas
            for f in raw_dir.glob("*.webm"):
                f.unlink()

            browser = await p.chromium.launch(
                headless=True,
                executable_path=CHROMIUM,
                args=["--no-sandbox"],
            )
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=str(raw_dir),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = await ctx.new_page()
            await _login(page)

            print(f"→ gravando {scene['id']} ({record_dur:.1f}s)")
            await page.goto(f"{BASE}{scene['route']}", wait_until="networkidle")
            await asyncio.sleep(1)
            if scene["scroll_y"]:
                await page.evaluate(
                    f"window.scrollTo({{top: {scene['scroll_y']}, behavior: 'smooth'}})"
                )
                await asyncio.sleep(1.2)

            action_start = time.time()
            if scene.get("action"):
                await _executar_acao(page, scene["action"])
                await asyncio.sleep(scene.get("wait_after_action", 1.0))

            elapsed = time.time() - action_start
            remaining = max(0.5, record_dur - elapsed - 1.0)
            await asyncio.sleep(remaining)

            await ctx.close()
            await browser.close()

            # localizar webm gravado
            webm_files = list(raw_dir.glob("*.webm"))
            if not webm_files:
                raise RuntimeError(f"nenhum webm gerado para {scene['id']}")
            webm = webm_files[0]
            print(f"  ✓ webm: {webm.name} ({webm.stat().st_size//1024} KB)")


# ---------------------------------------------------------------------------
# Fase 3: Composição via ffmpeg
# ---------------------------------------------------------------------------


def _drawtext_escape(s: str) -> str:
    """Escapa string para o filtro drawtext do ffmpeg."""
    return (
        s.replace("\\", "\\\\")
        .replace(":", r"\:")
        .replace("'", r"\\\'")
        .replace(",", r"\,")
        .replace("%", r"\%")
    )


def compor_cena(scene: Dict[str, Any], idx: int) -> Path:
    """Combina webm raw + audio + overlays em MP4 1920x1080 por cena."""
    audio_path = AUDIO_DIR / f"{scene['id']}.mp3"
    dur = duracao_audio(audio_path)
    raw_dir = RAW_DIR / scene["id"]
    webm = next(raw_dir.glob("*.webm"))
    out = SCENE_DIR / f"{scene['id']}.mp4"

    # Pula os primeiros N segundos do webm (login + navegação + primeiro scroll)
    # A duração do webm sempre é audio_dur + buffer, então há margem.
    skip = scene.get("video_skip", 4.5)

    top = _drawtext_escape(scene["caption_top"].upper())
    main = _drawtext_escape(scene["caption_main"])
    sub = _drawtext_escape(scene["caption_sub"])

    # Cores estilo bronze da paleta do app
    color_accent = "0xC9A66B"  # bronze
    color_strong = "white"
    color_muted = "0xAFA79A"

    vf = (
        # Escalar / cortar para 1920x1080 (o webm do Playwright já é 1920x1080)
        f"scale=1920:1080:force_original_aspect_ratio=increase,"
        f"crop=1920:1080,"
        # Barra inferior escura (draw rect) — alpha estático 72%
        f"drawbox=x=0:y=780:w=1920:h=300:color=black@0.72:t=fill,"
        # Uma linha bronze fina em cima da barra
        f"drawbox=x=120:y=810:w=200:h=2:color={color_accent}:t=fill,"
        # Top caption (mono, small, uppercase, accent color)
        f"drawtext=fontfile='{FONT_ITALIC}':text='{top}':"
        f"fontsize=22:fontcolor={color_accent}:"
        f"x=350:y=800,"
        # Main caption (Fraunces Bold Italic, huge)
        f"drawtext=fontfile='{FONT_ITALIC}':text='{main}':"
        f"fontsize=54:fontcolor={color_strong}:"
        f"x=120:y=850,"
        # Sub caption (Fraunces Bold, small, muted)
        f"drawtext=fontfile='{FONT_BOLD}':text='{sub}':"
        f"fontsize=22:fontcolor={color_muted}:"
        f"x=120:y=1010"
    )

    # Fade suave global de abertura e fechamento (cuida das transições entre cenas)
    vf_final = vf + f",fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.5}:d=0.5"

    cmd = [
        FFMPEG, "-y",
        "-ss", f"{skip:.2f}", "-i", str(webm),
        "-i", str(audio_path),
        "-t", f"{dur:.3f}",
        "-vf", vf_final,
        "-af", f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.3}:d=0.3",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(f"  ✓ cena {scene['id']} → {out.name} ({out.stat().st_size//1024} KB)")
    return out


def concatenar(cenas: List[Path]) -> Path:
    lst = OUT / "concat.txt"
    lst.write_text("\n".join(f"file '{c.absolute()}'" for c in cenas))
    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-c", "copy",
        str(FINAL),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(f"\n✓ vídeo final: {FINAL} ({FINAL.stat().st_size//1024} KB)")
    return FINAL


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    print("=" * 60)
    print("Fase 1: TTS")
    print("=" * 60)
    await gerar_tts()
    total_dur = sum(duracao_audio(AUDIO_DIR / f"{s['id']}.mp3") for s in SCENES)
    print(f"  duração total narração: {total_dur:.1f}s")

    print("\n" + "=" * 60)
    print("Fase 2: Gravação Playwright")
    print("=" * 60)
    await gravar_cenas()

    print("\n" + "=" * 60)
    print("Fase 3: Composição ffmpeg")
    print("=" * 60)
    cenas = []
    for i, scene in enumerate(SCENES):
        try:
            cenas.append(compor_cena(scene, i))
        except subprocess.CalledProcessError as e:
            print(f"  ✗ falha compondo {scene['id']}: {e.stderr[-600:]}")
            raise

    print("\n" + "=" * 60)
    print("Concatenando cenas")
    print("=" * 60)
    concatenar(cenas)


if __name__ == "__main__":
    asyncio.run(main())
