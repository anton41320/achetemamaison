"""Phase 11: Pack annonce premium (Stripe) — backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
SEED_PID = "6aa02db9efd8f90925a5a758"
RETURN_URL = f"{BASE_URL}/property/{SEED_PID}/pack"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- pack/status ---
def test_pack_status_shape(s):
    r = s.get(f"{API}/properties/{SEED_PID}/pack/status", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["property_id"] == SEED_PID
    assert d["price_cents"] == 4900
    assert d["currency"] == "eur"
    assert isinstance(d["payments_available"], bool)
    assert d["free_retouches"] == 1
    assert d["photos"] >= 1
    assert d["listings"] >= 1
    assert d["retouches_used"] >= 1
    # unlocked may be false (fresh) or true if a prior payment happened
    assert isinstance(d["unlocked"], bool)
    assert "last_order" in d


def test_pack_status_unknown_pid(s):
    r = s.get(f"{API}/properties/000000000000000000000000/pack/status", timeout=15)
    assert r.status_code == 404


# --- pack.pdf gating ---
def test_pack_pdf_gating(s):
    # First check if unlocked; if it is, we skip 402 assertion (seed may have been paid earlier).
    st = s.get(f"{API}/properties/{SEED_PID}/pack/status", timeout=15).json()
    r = s.get(f"{API}/properties/{SEED_PID}/pack.pdf", timeout=60, allow_redirects=False)
    if st["unlocked"]:
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1000
        # target price present, page 1 title mention (rudimentary check by scanning bytes)
        assert b"Prix" in r.content or b"250" in r.content
    else:
        assert r.status_code == 402, r.text


# --- checkout ---
def test_checkout_invalid_return_url(s):
    r = s.post(f"{API}/properties/{SEED_PID}/pack/checkout", json={"return_url": "foo"}, timeout=15)
    assert r.status_code == 422, r.text


def test_checkout_unknown_pid(s):
    r = s.post(f"{API}/properties/000000000000000000000000/pack/checkout",
               json={"return_url": RETURN_URL}, timeout=15)
    assert r.status_code == 404


def test_checkout_creates_session_or_conflict(s):
    """POST checkout: 201 with checkout_url when not unlocked, else 409."""
    st = s.get(f"{API}/properties/{SEED_PID}/pack/status", timeout=15).json()
    r = s.post(f"{API}/properties/{SEED_PID}/pack/checkout",
               json={"return_url": RETURN_URL}, timeout=30)
    if st["unlocked"]:
        assert r.status_code == 409, r.text
    else:
        assert r.status_code == 201, r.text
        body = r.json()
        assert "order_id" in body and body["order_id"]
        assert body["checkout_url"].startswith("https://checkout.stripe.com"), body["checkout_url"]


# --- regression ---
def test_regression_property(s):
    r = s.get(f"{API}/properties/{SEED_PID}", timeout=30)
    assert r.status_code == 200
    assert r.json().get("estimation")


def test_regression_next_steps(s):
    r = s.get(f"{API}/next-steps", timeout=30)
    assert r.status_code == 200
    assert "properties" in r.json()
