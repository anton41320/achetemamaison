"""Iteration 17 — origin outage resilience regression.

Only fast, read-only checks are done here. Never call POST /api/dvf/ingest
(would restart the heavy pipeline and saturate the pod).
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else None
if not BASE_URL:
    # Fallback: read frontend/.env
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL missing"

SEED_EMAIL = "delivered@resend.dev"
SEED_PASSWORD = "Estimo2026!"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# --- Health probes -----------------------------------------------------------

def test_root_health_fast(api):
    t0 = time.time()
    r = api.get(f"{BASE_URL}/health", timeout=5)
    dt = time.time() - t0
    assert r.status_code == 200
    assert dt < 1.5, f"/health too slow: {dt:.2f}s"


def test_api_health_fast(api):
    t0 = time.time()
    r = api.get(f"{BASE_URL}/api/health", timeout=5)
    dt = time.time() - t0
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
    assert dt < 1.5, f"/api/health too slow: {dt:.2f}s"


# --- DVF status: idle, populated, no job running ----------------------------

def test_dvf_status_idle_and_populated(api):
    r = api.get(f"{BASE_URL}/api/dvf/status", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["state"] == "idle", f"DVF not idle: {d['state']}"
    assert d["total"] > 100_000, f"DVF total too small: {d['total']}"
    # Data already exists so no auto-ingest was triggered at boot.


# --- Auth resilience wiring --------------------------------------------------

def test_auth_me_ok_with_seed_token(api, token):
    r = api.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["email"] == SEED_EMAIL


def test_auth_me_401_without_token(api):
    r = api.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 401


def test_login_wrong_password(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": SEED_EMAIL, "password": "wrong-Password-9"}, timeout=15)
    assert r.status_code == 401
    body = r.json()
    assert "incorrect" in (body.get("detail") or "").lower()


# --- Property listing works (front will exercise 503/abort via route mocking) --

def test_list_properties_ok(api, token):
    r = api.get(f"{BASE_URL}/api/properties", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_property_detail_ok(api, token):
    r = api.get(
        f"{BASE_URL}/api/properties/6aa02db9efd8f90925a5a758",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert r.status_code == 200
    d = r.json()
    assert d.get("estimation") is not None
    assert d["estimation"].get("value")


# --- Code-review checks (static) --------------------------------------------

def test_jobs_delay_and_nice():
    src = open("/app/backend/jobs.py").read()
    assert "time.sleep(delay_s)" in src
    assert "os.nice(10)" in src
    assert "delay_s: float = 45.0" in src  # default 45 s
    assert "delay_s: float = 30.0" in src  # models default 30 s


def test_ingest_endpoint_uses_zero_delay():
    src = open("/app/backend/server.py").read()
    # POST /api/dvf/ingest passes 0.0 (immediate) delay
    assert "jobs.start(jobs.ingest_then_train, mongo_url, db_name, DVF_DEPARTMENTS, DVF_YEARS, 0.0)" in src


def test_dvf_download_streaming():
    src = open("/app/backend/dvf_ingest.py").read()
    assert "stream=True" in src
    assert '.part' in src or 'with_suffix(".part")' in src
