"""Captures brutes des 7 écrans de l'app (format téléphone 390×844 @3x → 1170×2532, puis redimensionnées 1320×2868 pour compose.py).
Compte démo Premium. Sortie : store-assets/raw/NN-label.png. Usage : python scripts/capture_store_shots.py [BASE_URL] [PROPERTY_ID]
"""
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://estimate-home.preview.emergentagent.com"
PID = sys.argv[2] if len(sys.argv) > 2 else "6adb22c2efdddf3e17bb468f"
TABLET = os.environ.get("TABLET") == "1"
OUT = "/app/store-assets/raw-ipad" if TABLET else "/app/store-assets/raw"
VIEWPORT = {"width": 1032, "height": 1376} if TABLET else {"width": 390, "height": 844}
SIZE = (2064, 2752) if TABLET else (1320, 2868)
EMAIL, PASSWORD = "demo@achetemamaison.fr", "Premium2026!"
os.makedirs(OUT, exist_ok=True)


def shot(page, name, wait_text=None, settle=2500):
    if wait_text:
        page.wait_for_selector(f"#root >> text={wait_text}", timeout=60000)
    page.wait_for_timeout(settle)
    tmp = f"/tmp/{name}.png"
    page.screenshot(path=tmp)
    Image.open(tmp).convert("RGB").resize(SIZE, Image.LANCZOS).save(f"{OUT}/{name}.png", optimize=True)
    print("shot", name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2 if TABLET else 3)
    page.goto(f"{BASE}/welcome", wait_until="domcontentloaded", timeout=90000)
    shot(page, "01-welcome", "Ou téléchargez", 4000)

    page.goto(f"{BASE}/sign-in", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("[data-testid='signin-email']", timeout=60000)
    page.get_by_test_id("signin-email").fill(EMAIL)
    page.get_by_test_id("signin-password").fill(PASSWORD)
    page.get_by_test_id("signin-submit").click()
    page.wait_for_selector("[data-testid='home-screen']", timeout=60000)
    shot(page, "02-home", "Mes biens", 4000)

    page.goto(f"{BASE}/property/{PID}", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("[data-testid='property-detail-screen']", timeout=60000)
    page.wait_for_timeout(3000)
    if page.locator("[data-testid='review-later']").count():
        page.get_by_test_id("review-later").click()
        page.wait_for_timeout(800)
    shot(page, "03-property", None, 2500)

    page.goto(f"{BASE}/property/{PID}/comparables", wait_until="domcontentloaded", timeout=90000)
    shot(page, "04-comparables", None, 5000)

    page.goto(f"{BASE}/property/{PID}/dossier", wait_until="domcontentloaded", timeout=90000)
    shot(page, "05-dossier", None, 4000)

    page.goto(f"{BASE}/property/{PID}/pack", wait_until="domcontentloaded", timeout=90000)
    shot(page, "06-pack", None, 4000)

    page.goto(f"{BASE}/property/{PID}/photos", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("[data-testid='photos-screen']", timeout=60000)
    page.wait_for_selector("[data-testid='photo-card-0']", timeout=60000)
    page.evaluate("""() => { const el = document.querySelector("[data-testid='photo-grid']"); el.scrollIntoView({ block: 'start', behavior: 'instant' });
        let p = el.parentElement; while (p && !(p.scrollHeight > p.clientHeight + 4)) p = p.parentElement; (p || window).scrollBy(0, -70); }""")
    shot(page, "07-photos", None, 4000)
    browser.close()
