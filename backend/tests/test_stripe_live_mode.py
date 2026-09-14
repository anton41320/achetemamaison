"""Iteration 13 — Verify Stripe LIVE mode switch WITHOUT completing any payment."""
import os
import requests
import pytest

BASE = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else "https://estimate-home.preview.emergentagent.com"
API = f"{BASE}/api"

TARGET_PID = "6aa02c492f09d3116cfaf507"       # locked Blois property
PAID_PID = "6aa02db9efd8f90925a5a758"          # unlocked from earlier test-mode payment
RETURN_URL = f"https://estimate-home.preview.emergentagent.com/property/{TARGET_PID}/pack"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# --- Live mode flags on locked property ---
def test_pack_status_live_mode(s):
    r = s.get(f"{API}/properties/{TARGET_PID}/pack/status", timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["mode"] == "live", d
    assert d["payments_available"] is True, d
    assert d["webhook_configured"] is False, d
    assert d["unlocked"] is False, d


# --- Create a LIVE checkout session (NO payment executed) ---
_created = {}

def test_pack_checkout_live_session(s):
    r = s.post(f"{API}/properties/{TARGET_PID}/pack/checkout", json={"return_url": RETURN_URL}, timeout=30)
    assert r.status_code in (200, 201), r.text
    d = r.json()
    assert "checkout_url" in d and "order_id" in d, d
    url = d["checkout_url"]
    assert url.startswith("https://checkout.stripe.com/c/pay/cs_live_"), f"Expected LIVE checkout URL, got: {url}"
    _created["order_id"] = d["order_id"]
    _created["url"] = url


# --- Polling with the live key must not error ---
def test_pack_status_after_live_checkout(s):
    r = s.get(f"{API}/properties/{TARGET_PID}/pack/status", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["mode"] == "live"
    assert d["unlocked"] is False
    lo = d.get("last_order")
    assert lo is not None, "expected a last_order after checkout creation"
    assert lo.get("status") == "pending", lo


# --- Regression: previously test-paid property remains unlocked ---
def test_regression_test_mode_paid_property_still_unlocked(s):
    r = s.get(f"{API}/properties/{PAID_PID}/pack/status", timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unlocked"] is True, d


def test_regression_pack_pdf_still_downloads(s):
    r = s.get(f"{API}/properties/{PAID_PID}/pack.pdf", timeout=60)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
    assert len(r.content) > 1024
