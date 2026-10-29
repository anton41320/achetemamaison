"""Iter 29 — photo endpoints ownership (auth.own()) + owner upload/delete round-trip.

- Second user (fresh register) : GET /properties/{pid}/photos -> [] ; DELETE /photos/{foreign} -> 404 ; photo still listed for owner
- Second user : POST upload / PATCH label / cover / reorder on foreign bien/photo -> 404
- Owner : POST multipart JPEG -> 201, listed, DELETE -> 200 then absent
- Cleanup : DELETE /api/auth/account for the second user
"""
import io
import os
import uuid

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PROP_ID = "6aa02db9efd8f90925a5a758"
FOREIGN_PHOTO = "6aa10ee21f38608802dce39f"
EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"
OTHER_PASSWORD = "TEST_Str0ng!Pass2026"


def _jpeg(w=800, h=600) -> bytes:
    buf = io.BytesIO()
    Image.effect_noise((w, h), 60).convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _token(d: dict) -> str:
    return d.get("access_token") or d.get("token")


@pytest.fixture(scope="module")
def owner():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {_token(r.json())}"}


@pytest.fixture(scope="module")
def other():
    email = f"test_iter29_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": OTHER_PASSWORD}, timeout=20)
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {_token(r.json())}"}
    yield h
    d = requests.delete(f"{API}/auth/account", json={"password": OTHER_PASSWORD}, headers=h, timeout=20)
    print(f"cleanup second user: {d.status_code} {d.text[:100]}")


# Ownership — list
def test_other_user_lists_no_photos(other):
    r = requests.get(f"{API}/properties/{PROP_ID}/photos", headers=other, timeout=20)
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        assert r.json() == []


# Ownership — delete foreign photo
def test_other_user_cannot_delete_foreign_photo(other, owner):
    before = [p["id"] for p in requests.get(f"{API}/properties/{PROP_ID}/photos", headers=owner, timeout=20).json()]
    assert FOREIGN_PHOTO in before, "reference photo missing from owner's list"
    r = requests.delete(f"{API}/photos/{FOREIGN_PHOTO}", headers=other, timeout=20)
    assert r.status_code == 404, r.text
    after = [p["id"] for p in requests.get(f"{API}/properties/{PROP_ID}/photos", headers=owner, timeout=20).json()]
    assert FOREIGN_PHOTO in after


# Ownership — other mutating endpoints
def test_other_user_cannot_upload_to_foreign_bien(other):
    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=other,
                      files={"file": ("t.jpg", _jpeg(), "image/jpeg")}, timeout=60)
    assert r.status_code == 404, r.text


def test_other_user_cannot_label_cover_reorder(other):
    assert requests.patch(f"{API}/photos/{FOREIGN_PHOTO}", json={"label": "Salon"}, headers=other, timeout=20).status_code in (404, 422)
    assert requests.post(f"{API}/photos/{FOREIGN_PHOTO}/cover", headers=other, timeout=20).status_code == 404
    assert requests.put(f"{API}/properties/{PROP_ID}/photos/order", json={"ids": [FOREIGN_PHOTO]}, headers=other, timeout=20).status_code == 404
    assert requests.post(f"{API}/properties/{PROP_ID}/photos/autosort", headers=other, timeout=20).status_code == 404


def test_unauthenticated_list_rejected():
    r = requests.get(f"{API}/properties/{PROP_ID}/photos", timeout=20)
    assert r.status_code == 401


# Owner round-trip
def test_owner_upload_then_delete(owner):
    r = requests.post(f"{API}/properties/{PROP_ID}/photos", headers=owner,
                      files={"file": ("TEST_iter29.jpg", _jpeg(), "image/jpeg")}, timeout=90)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["property_id"] == PROP_ID
    ids = [p["id"] for p in requests.get(f"{API}/properties/{PROP_ID}/photos", headers=owner, timeout=20).json()]
    assert pid in ids
    d = requests.delete(f"{API}/photos/{pid}", headers=owner, timeout=20)
    assert d.status_code == 200 and d.json() == {"deleted": True}
    ids = [p["id"] for p in requests.get(f"{API}/properties/{PROP_ID}/photos", headers=owner, timeout=20).json()]
    assert pid not in ids
    assert requests.delete(f"{API}/photos/{pid}", headers=owner, timeout=20).status_code == 404
