"""Iter 24 sanity backend tests.

Covers:
- GET /api/properties/{pid}/environment (cached, <3s, 200)
- GET /api/properties/{pid} -> estimation.low == round(value*0.95, 1000), high == round(value*1.05, 1000)
- POST /api/properties/{pid}/photos multipart JPEG -> 201 + listed in GET /photos
- DELETE /api/photos/{photo_id}
"""
import io
import os
import time

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PROP_ID = "6aa3f68d440f04920cdaffde"
EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"


@pytest.fixture(scope="module")
def token() -> str:
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _round1000(x: float) -> float:
    return float(int(round(x / 1000)) * 1000)


# ---- environment cache ----
def test_environment_cached_under_3s(auth):
    t0 = time.time()
    r = requests.get(f"{API}/properties/{PROP_ID}/environment", headers=auth, timeout=30)
    dt = time.time() - t0
    assert r.status_code == 200, r.text
    assert dt < 3.0, f"environment should be cached (<3s), took {dt:.2f}s"
    body = r.json()
    assert body.get("cached") is True, f"expected cached=True, got {body.get('cached')}"
    report = body.get("report") or {}
    sections = report.get("sections") or {}
    assert sections, "report.sections empty"


# ---- estimation band ----
def test_estimation_band_pm5_rounded(auth):
    r = requests.get(f"{API}/properties/{PROP_ID}", headers=auth, timeout=30)
    assert r.status_code == 200, r.text
    est = r.json().get("estimation") or {}
    v, lo, hi = est.get("value"), est.get("low"), est.get("high")
    assert v and lo and hi, f"missing estimation fields: {est}"
    expected_low = _round1000(v * 0.95)
    expected_high = _round1000(v * 1.05)
    # tolerate ±1000 € because of multiple nested roundings (base * env_pct)
    assert abs(lo - expected_low) <= 1000, f"low={lo} expected ~{expected_low} (value={v})"
    assert abs(hi - expected_high) <= 1000, f"high={hi} expected ~{expected_high} (value={v})"


# ---- photo upload lifecycle ----
def _make_jpeg(w=640, h=480) -> bytes:
    img = Image.new("RGB", (w, h), (120, 160, 200))
    for i in range(0, w, 20):
        for j in range(0, h, 20):
            img.putpixel((i, j), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def test_photo_upload_and_delete(auth):
    jpg = _make_jpeg()
    files = {"file": ("TEST_iter24.jpg", jpg, "image/jpeg")}
    # count before
    before = requests.get(f"{API}/properties/{PROP_ID}/photos", headers=auth, timeout=20)
    assert before.status_code == 200
    n_before = len(before.json())

    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=auth, files=files, timeout=60)
    assert r.status_code == 201, f"upload failed: {r.status_code} {r.text}"
    photo = r.json()
    pid = photo.get("id")
    assert pid, f"no id in response: {photo}"

    # listed
    lst = requests.get(f"{API}/properties/{PROP_ID}/photos", headers=auth, timeout=20)
    assert lst.status_code == 200
    ids = [p.get("id") for p in lst.json()]
    assert pid in ids, f"uploaded photo {pid} not listed"
    assert len(lst.json()) == n_before + 1

    # cleanup
    d = requests.delete(f"{API}/photos/{pid}", headers=auth, timeout=20)
    assert d.status_code in (200, 204), f"delete failed: {d.status_code} {d.text}"

    # verify gone
    after = requests.get(f"{API}/properties/{PROP_ID}/photos", headers=auth, timeout=20)
    assert after.status_code == 200
    assert pid not in [p.get("id") for p in after.json()]
    assert len(after.json()) == n_before
