"""Generate LinkedIn carousel screenshots (1080x1080) and bundle into a single PDF."""
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

BASE = "https://tributaria-core.preview.emergentagent.com"
EMAIL = "admin@fiscalcore.local"
PASSWORD = "FiscalCore@2026"

OUT_DIR = Path("/app/carousel")
OUT_DIR.mkdir(exist_ok=True)

# Each slide: (filename, route, scroll_to_y, wait_ms, extra_action)
SLIDES = [
    ("slide-1-hero.jpg",       "/",           0,    1500, None),
    ("slide-2-pilares.jpg",    "/",           900,  1000, None),
    ("slide-3-totais.jpg",     "/",           1600, 2500, "calcular"),
    ("slide-4-ledger.jpg",     "/auditoria",  0,    2500, "verificar"),
    ("slide-5-delta.jpg",      "/simulador",  0,    2500, "simular"),
    ("slide-6-assinatura.jpg", "/sobre",      0,    1500, None),
]


def login(page):
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.wait_for_selector('[data-testid="login-email"]', timeout=15000)
    page.fill('[data-testid="login-email"]', EMAIL)
    page.fill('[data-testid="login-password"]', PASSWORD)
    page.click('[data-testid="login-submit"]')
    page.wait_for_url(f"{BASE}/", timeout=15000)
    time.sleep(2)


def do_extra(page, action):
    try:
        if action == "calcular":
            # Playground: click the "Calcular" primary button
            btn = page.query_selector('button:has-text("Calcular")')
            if btn:
                btn.click()
                time.sleep(2)
        elif action == "verificar":
            btn = page.query_selector('button:has-text("Verificar")')
            if btn:
                btn.click()
                time.sleep(2)
        elif action == "simular":
            btn = page.query_selector('button:has-text("Simular")') or page.query_selector('button:has-text("Comparar")')
            if btn:
                btn.click()
                time.sleep(2)
    except Exception as e:
        print(f"  extra action '{action}' skipped: {e}")


def crop_square(path: Path):
    """Ensure final image is 1080x1080 by center-cropping if needed."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if (w, h) == (1080, 1080):
        return
    side = min(w, h)
    left = (w - side) // 2
    top = 0  # keep top of the page (headers/content)
    img = img.crop((left, top, left + side, top + side))
    if img.size != (1080, 1080):
        img = img.resize((1080, 1080), Image.LANCZOS)
    img.save(path, "JPEG", quality=92)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/pw-browsers/chromium_headless_shell-1208/chrome-linux/headless_shell",
            args=["--no-sandbox"],
        )
        ctx = browser.new_context(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        page = ctx.new_page()

        print("→ Login...")
        login(page)

        for name, route, scroll_y, wait_ms, action in SLIDES:
            print(f"→ {name}  route={route}")
            page.goto(f"{BASE}{route}", wait_until="networkidle")
            time.sleep(1)
            if action:
                do_extra(page, action)
            if scroll_y:
                page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'instant'}})")
            time.sleep(wait_ms / 1000)
            out = OUT_DIR / name
            page.screenshot(path=str(out), type="jpeg", quality=92, full_page=False)
            crop_square(out)

        browser.close()

    # Build PDF from JPGs (in slide order)
    pdf_path = Path("/app/FiscalCore-LinkedIn-Carousel.pdf")
    imgs = []
    for name, *_ in SLIDES:
        img = Image.open(OUT_DIR / name).convert("RGB")
        imgs.append(img)
    imgs[0].save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=imgs[1:])
    print(f"\n✓ PDF gerado: {pdf_path}  ({pdf_path.stat().st_size // 1024} KB)")
    print(f"✓ JPGs individuais em: {OUT_DIR}/")


if __name__ == "__main__":
    main()
