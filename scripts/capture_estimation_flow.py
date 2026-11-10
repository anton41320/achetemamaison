"""Capture les vraies pages du site (parcours estimation gratuite) en format téléphone.
Sortie : /tmp/realshots/NN-label.png (780×1688, échelle 2). Usage : python scripts/capture_estimation_flow.py [BASE_URL]
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://estimate-home.preview.emergentagent.com"
OUT = "/tmp/realshots"
os.makedirs(OUT, exist_ok=True)
ADDRESS = "12 rue de la Gare 41000 Blois"


def shot(page, name, test_id="free-estimate", offset=-12):
    if test_id:
        page.evaluate(
            """([id, off]) => { const el = document.querySelector(`[data-testid="${id}"]`); if (!el) return;
                el.scrollIntoView({ block: 'start', behavior: 'instant' });
                let p = el.parentElement;
                while (p && !(p.scrollHeight > p.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(p).overflowY))) p = p.parentElement;
                (p || window).scrollBy(0, off); }""",
            [test_id, offset],
        )
        page.wait_for_timeout(500)
    page.screenshot(path=f"{OUT}/{name}.png")
    print("shot", name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page.goto(f"{BASE}/estimation-maison", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("#root >> text=/adresse/i", timeout=90000)
    page.wait_for_timeout(3000)
    shot(page, "01-landing", test_id=None)
    shot(page, "02-step1-empty")

    addr = page.get_by_test_id("address-input")
    addr.click()
    for i, ch in enumerate(ADDRESS):
        addr.type(ch, delay=0)
        if i == 10:
            shot(page, "03-step1-typing")
    page.wait_for_selector("[data-testid='address-result-0']", timeout=30000)
    page.wait_for_timeout(600)
    shot(page, "04-step1-results")
    page.get_by_test_id("address-result-0").click()
    page.wait_for_selector("[data-testid='address-selected']", timeout=20000)
    page.wait_for_timeout(600)
    shot(page, "05-step1-selected")
    page.get_by_test_id("step-continue-button").click()
    page.wait_for_selector("[data-testid='surface-input']", timeout=20000)
    page.wait_for_timeout(500)
    shot(page, "06-step2-empty")
    page.get_by_test_id("surface-input").fill("128")
    page.wait_for_timeout(400)
    shot(page, "07-step2-filled")
    page.get_by_test_id("step-continue-button").click()
    page.wait_for_selector("[data-testid='year-input']", timeout=20000)
    page.wait_for_timeout(500)
    page.get_by_test_id("year-input").fill("1998")
    page.get_by_text("Bon état", exact=True).first.click()
    if page.get_by_test_id("land-input").count():
        page.get_by_test_id("land-input").fill("650")
    page.wait_for_timeout(500)
    shot(page, "08-step3-filled")
    page.get_by_test_id("step-continue-button").click()
    page.wait_for_timeout(900)
    shot(page, "09-step4")
    page.get_by_test_id("estimate-submit-button").click()
    t0 = time.time()
    try:
        page.wait_for_timeout(700)
        shot(page, "10-loading")
    except Exception:
        pass
    page.wait_for_selector("[data-testid='free-result-value']", timeout=120000)
    print("estimation en", round(time.time() - t0, 1), "s")
    page.wait_for_timeout(1500)
    shot(page, "11-result", test_id="free-result", offset=-90)
    if page.get_by_test_id("free-adjustments").count():
        shot(page, "12-adjustments", test_id="free-adjustments", offset=-40)
    shot(page, "13-mascot", test_id="free-result-mascot", offset=-200)
    browser.close()
