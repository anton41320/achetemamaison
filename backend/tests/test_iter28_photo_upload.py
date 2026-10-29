"""Iter 28 — photo upload (web 520 bug fix) backend checks.

- GET /api/health -> status ok + started_at + uptime_s
- POST /api/properties/{pid}/photos multipart JPEG -> 201 ; persisted in GET /photos ; stored file <= 1600 px (server normalize)
- POST large 4000x3000 JPEG -> 201 (server accepts, normalizes)
- POST invalid file -> 422 (not 5xx)
- DELETE /api/photos/{id} -> deleted, then absent from list
"""
import io
import os

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PROP_ID = "6aa02db9efd8f90925a5a758"
EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"


def _jpeg(w: int, h: int, quality: int = 95) -> bytes:
    img = Image.effect_noise((w, h), 60).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"}


@pytest.fixture(scope="module")
def created(auth):
    ids: list[str] = []
    yield ids
    for pid in ids:
        requests.delete(f"{API}/photos/{pid}", headers=auth, timeout=20)


# Health
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "ok"
    assert isinstance(d.get("started_at"), str) and d["started_at"]
    assert isinstance(d.get("uptime_s"), int) and d["uptime_s"] >= 0


# Upload small JPEG
def test_upload_small_jpeg(auth, created):
    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=auth,
                      files={"file": ("TEST_small.jpg", _jpeg(800, 600), "image/jpeg")}, timeout=60)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["property_id"] == PROP_ID and p["status"] == "original" and "_id" not in p
    created.append(p["id"])
    lst = requests.get(f"{API}/properties/{PROP_ID}/photos", headers=auth, timeout=20).json()
    assert p["id"] in [x["id"] for x in lst]
    f = requests.get(f"{API}/files/{p['original_path']}", headers=auth, timeout=30)
    assert f.status_code == 200
    assert Image.open(io.BytesIO(f.content)).size == (800, 600)


# Upload large JPEG (unresized, like before the client fix)
def test_upload_large_jpeg(auth, created):
    raw = _jpeg(4000, 3000)
    assert len(raw) > 3 * 1024 * 1024
    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=auth,
                      files={"file": ("TEST_large.jpg", raw, "image/jpeg")}, timeout=120)
    assert r.status_code == 201, r.text
    p = r.json()
    created.append(p["id"])
    f = requests.get(f"{API}/files/{p['original_path']}", headers=auth, timeout=30)
    assert max(Image.open(io.BytesIO(f.content)).size) <= 1600


# Invalid file -> 422 (no 5xx)
def test_upload_invalid_file(auth):
    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=auth,
                      files={"file": ("TEST_bad.jpg", b"not an image", "image/jpeg")}, timeout=30)
    assert r.status_code == 422
    assert "illisible" in r.json()["detail"]


# Unknown property -> 404
def test_upload_unknown_property(auth):
    r = requests.post(f"{API}/properties/000000000000000000000000/photos", headers=auth,
                      files={"file": ("TEST.jpg", _jpeg(100, 100), "image/jpeg")}, timeout=30)
    assert r.status_code == 404


# Delete -> absent from list
def test_delete_photo(auth, created):
    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=auth,
                      files={"file": ("TEST_del.jpg", _jpeg(200, 200), "image/jpeg")}, timeout=60)
    assert r.status_code == 201
    pid = r.json()["id"]
    d = requests.delete(f"{API}/photos/{pid}", headers=auth, timeout=20)
    assert d.status_code == 200 and d.json() == {"deleted": True}
    lst = requests.get(f"{API}/properties/{PROP_ID}/photos", headers=auth, timeout=20).json()
    assert pid not in [x["id"] for x in lst]
    assert requests.delete(f"{API}/photos/{pid}", headers=auth, timeout=20).status_code == 404
