"""Phase 5 — Photos upload + retouch + soft delete + /files serving."""
from __future__ import annotations

import io
import os
import time

import pytest
import requests
from PIL import Image

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
DEMO_PROPERTY_ID = "6aa02db9efd8f90925a5a758"


def _jpeg_bytes(size=(320, 240), color=(200, 120, 90)) -> bytes:
    img = Image.new("RGB", size, color)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


@pytest.fixture(scope="module")
def created_photo_id():
    """Upload a test JPEG that we can delete later. Yields the photo id and cleans up."""
    files = {"file": ("test_TEST.jpg", _jpeg_bytes(), "image/jpeg")}
    r = requests.post(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", files=files, timeout=60)
    assert r.status_code == 201, f"upload failed: {r.status_code} {r.text}"
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{API}/photos/{pid}", timeout=15)


# ---------------- Upload ----------------
class TestPhotoUpload:
    def test_upload_returns_201_with_expected_shape(self):
        files = {"file": ("TEST_upload.jpg", _jpeg_bytes(), "image/jpeg")}
        r = requests.post(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", files=files, timeout=60)
        assert r.status_code == 201, r.text
        d = r.json()
        assert "id" in d and isinstance(d["id"], str)
        assert d["original_path"].startswith("estimo/properties/"), d["original_path"]
        assert d["status"] == "original"
        assert d["retouched_path"] is None
        # Cleanup this specific upload
        del_r = requests.delete(f"{API}/photos/{d['id']}", timeout=15)
        assert del_r.status_code == 200

    def test_upload_non_image_returns_422(self):
        files = {"file": ("not_an_image.txt", b"just text, not an image", "text/plain")}
        r = requests.post(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", files=files, timeout=30)
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"

    def test_upload_unknown_property_returns_404(self):
        files = {"file": ("TEST_x.jpg", _jpeg_bytes(), "image/jpeg")}
        # Valid ObjectId shape but nonexistent
        r = requests.post(f"{API}/properties/6aa02db9efd8f90925a5a999/photos", files=files, timeout=30)
        assert r.status_code == 404, r.text

    def test_upload_invalid_objectid_returns_404(self):
        files = {"file": ("TEST_x.jpg", _jpeg_bytes(), "image/jpeg")}
        r = requests.post(f"{API}/properties/not-an-oid/photos", files=files, timeout=30)
        assert r.status_code == 404


# ---------------- List + file serving ----------------
class TestPhotoListAndFiles:
    def test_list_photos_contains_created(self, created_photo_id):
        r = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", timeout=15)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert created_photo_id in ids

    def test_files_endpoint_serves_original(self, created_photo_id):
        r = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", timeout=15)
        photo = next(p for p in r.json() if p["id"] == created_photo_id)
        f = requests.get(f"{API}/files/{photo['original_path']}", timeout=30)
        assert f.status_code == 200
        assert f.headers.get("Content-Type", "").startswith("image/jpeg")
        assert len(f.content) > 100

    def test_files_unknown_returns_404(self):
        r = requests.get(f"{API}/files/unknown/path.jpg", timeout=15)
        assert r.status_code == 404


# ---------------- Retouch ----------------
class TestPhotoRetouch:
    """ONE retouch call only (LLM credits). Uses a fresh upload we then delete."""

    def test_retouch_success(self):
        # Upload dedicated photo for retouch
        files = {"file": ("TEST_retouch.jpg", _jpeg_bytes((400, 300), (180, 200, 160)), "image/jpeg")}
        up = requests.post(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", files=files, timeout=60)
        assert up.status_code == 201
        pid = up.json()["id"]
        try:
            t0 = time.time()
            r = requests.post(f"{API}/photos/{pid}/retouch", timeout=90)
            elapsed = time.time() - t0
            assert r.status_code == 200, f"retouch failed ({elapsed:.1f}s): {r.status_code} {r.text}"
            d = r.json()
            assert d["status"] == "done"
            assert d["retouched_path"], "retouched_path missing"
            assert d["model"] == "gemini-3.1-flash-image-preview"
            # Serve retouched file
            f = requests.get(f"{API}/files/{d['retouched_path']}", timeout=30)
            assert f.status_code == 200
            assert f.headers.get("Content-Type", "").startswith("image/jpeg")
        finally:
            requests.delete(f"{API}/photos/{pid}", timeout=15)

    def test_retouch_unknown_photo_returns_404(self):
        r = requests.post(f"{API}/photos/6aa02db9efd8f90925a5a999/retouch", timeout=15)
        assert r.status_code == 404


# ---------------- Delete ----------------
class TestPhotoDelete:
    def test_delete_and_second_delete_404(self):
        files = {"file": ("TEST_delete.jpg", _jpeg_bytes(), "image/jpeg")}
        up = requests.post(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", files=files, timeout=30)
        assert up.status_code == 201
        pid = up.json()["id"]
        r1 = requests.delete(f"{API}/photos/{pid}", timeout=15)
        assert r1.status_code == 200
        assert r1.json() == {"deleted": True}
        # Not in list anymore
        lst = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}/photos", timeout=15).json()
        assert pid not in [p["id"] for p in lst]
        # Second delete = 404
        r2 = requests.delete(f"{API}/photos/{pid}", timeout=15)
        assert r2.status_code == 404


# ---------------- Regression ----------------
class TestRegression:
    def test_property_detail_still_ok(self):
        r = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("estimation") is not None
        est = d["estimation"]
        assert est.get("low") is not None and est.get("high") is not None
        assert est.get("value") is not None
