"""Iteration 14 — Verify Stripe LIVE checkout creates order only on success, no dangling rows, invalid input yields 422."""
import os
import requests
import pytest

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

TARGET_PID = "6aa02c492f09d3116cfaf507"
RETURN_URL = f"https://estimate-home.preview.emergentagent.com/property/{TARGET_PID}/pack"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def test_checkout_success_returns_live_cs_url(s):
    r = s.post(f"{API}/properties/{TARGET_PID}/pack/checkout",
               json={"return_url": RETURN_URL}, timeout=30)
    assert r.status_code == 201, (r.status_code, r.text)
    d = r.json()
    assert "checkout_url" in d and "order_id" in d, d
    assert d["checkout_url"].startswith("https://checkout.stripe.com/c/pay/cs_live_"), d["checkout_url"]


def test_status_last_order_reflects_created_pending(s):
    r = s.get(f"{API}/properties/{TARGET_PID}/pack/status", timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["mode"] == "live", d
    assert d["unlocked"] is False, d
    lo = d.get("last_order")
    assert lo is not None, d
    assert lo.get("status") == "pending", lo


def test_invalid_return_url_returns_422_and_does_not_create_order(s):
    # Snapshot current last_order id
    before = s.get(f"{API}/properties/{TARGET_PID}/pack/status", timeout=20).json()
    before_order_id = (before.get("last_order") or {}).get("order_id")

    r = s.post(f"{API}/properties/{TARGET_PID}/pack/checkout",
               json={"return_url": "foo"}, timeout=20)
    assert r.status_code == 422, (r.status_code, r.text)

    after = s.get(f"{API}/properties/{TARGET_PID}/pack/status", timeout=20).json()
    after_order_id = (after.get("last_order") or {}).get("order_id")

    # last_order must not have changed (no new order created)
    assert before_order_id == after_order_id, (before_order_id, after_order_id)
