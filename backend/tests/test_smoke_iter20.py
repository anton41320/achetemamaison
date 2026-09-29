"""Smoke tests for iteration 20: welcome flow + property detail updates.

Verifies:
 - GET /api/properties returns 200 with 'completion'
 - PUT /api/properties/{id}/target with target_price=250000 returns 200
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"
PROPERTY_ID = "6aa02db9efd8f90925a5a758"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token") or data.get("session", {}).get("token")
    assert tok, f"no token in {data}"
    return tok


@pytest.fixture()
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- Properties list ---
def test_properties_list_ok(auth_headers):
    r = requests.get(f"{BASE_URL}/api/properties", headers=auth_headers, timeout=20)
    assert r.status_code == 200, r.text
    props = r.json()
    assert isinstance(props, list)
    assert len(props) > 0, "expected at least one property"
    assert "completion" in props[0], f"expected 'completion' in property, got keys: {list(props[0].keys())}"


# --- Property detail smoke ---
def test_property_detail_ok(auth_headers):
    r = requests.get(f"{BASE_URL}/api/properties/{PROPERTY_ID}", headers=auth_headers, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("id") == PROPERTY_ID
    assert "estimation" in data


# --- Target price PUT ---
def test_put_target_price_ok(auth_headers):
    r = requests.put(
        f"{BASE_URL}/api/properties/{PROPERTY_ID}/target",
        headers=auth_headers,
        json={"target_price": 250000},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # response may contain target_price or analysis; verify at least one
    assert "target_price" in data or "analysis" in data, f"unexpected payload keys: {list(data.keys())}"
