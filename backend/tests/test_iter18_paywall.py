"""Iteration 18 backend tests — rebranding + hard paywall on every AI tool.

Covers:
- POST /api/auth/login (seed account)
- Health branding: /api/health.app == "Achètes ma maison"
- Locked property 6aa3f68d440f04920cdaffde:
    * GET /api/properties/{id}/pack/status -> unlocked=false, free_retouches=0
    * POST /api/properties/{id}/listings -> 402 with detail starting with 'Pack annonce premium requis (49 €)'
    * POST /api/properties/{id}/documents -> 201, ocr_status='locked', status='a_verifier'
    * POST /api/documents/{did}/reocr -> 402
    * DELETE /api/documents/{did} -> 200
    * Photos: if none, upload one, then POST /api/photos/{id}/retouch -> 402 + DELETE
- Regression on unlocked property (if any):
    * GET /api/properties/{id}/pack.pdf -> 200 application/pdf
- PDF branding (locked property is fine):
    * GET /api/properties/{id}/report.pdf -> 200, page 1 text contains 'Achètes ma maison · Rapport d'estimation' + at least one image
    * GET /api/properties/{id}/notaire.pdf -> 200
"""
from __future__ import annotations

import io
import os

import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
SEED_EMAIL = "delivered@resend.dev"
SEED_PASSWORD = "Estimo2026!"
LOCKED_PID = "6aa3f68d440f04920cdaffde"


@pytest.fixture(scope="session")
def token() -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": SEED_EMAIL, "password": SEED_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, r.text
    return tok


@pytest.fixture(scope="session")
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def small_jpeg() -> bytes:
    """Minimal valid JPEG (created via PIL if available, else canned bytes)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(200, 100, 50)).save(buf, format="JPEG", quality=70)
    return buf.getvalue()


# ---------------- Branding ----------------

class TestBranding:
    def test_health_app_name(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("app") == "Achètes ma maison", r.json()


# ---------------- Locked property paywall ----------------

class TestLockedPack:
    def test_pack_status_locked(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/properties/{LOCKED_PID}/pack/status",
                         headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["unlocked"] is False, data
        assert data["free_retouches"] == 0, data
        assert data["price_cents"] == 4900, data

    def test_listing_402_paywall(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/properties/{LOCKED_PID}/listings",
                          headers=auth_headers,
                          json={"style": "sobre", "include_price": True, "extra_facts": None},
                          timeout=30)
        assert r.status_code == 402, r.text
        detail = r.json().get("detail", "")
        assert detail.startswith("Pack annonce premium requis (49 €)"), detail

    def test_document_upload_locked_then_reocr_402_then_delete(self, auth_headers, small_jpeg):
        # Upload a jpeg to a locked property; must return 201 with ocr_status='locked' and status='a_verifier'.
        files = {"file": ("test.jpg", small_jpeg, "image/jpeg")}
        data = {"item_key": "dpe"}
        r = requests.post(f"{BASE_URL}/api/properties/{LOCKED_PID}/documents",
                          headers=auth_headers, files=files, data=data, timeout=30)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body.get("ocr_status") == "locked", body
        assert body.get("status") == "a_verifier", body
        did = body.get("id") or body.get("_id")
        assert did, body

        try:
            # Reocr must return 402 (paywall).
            r2 = requests.post(f"{BASE_URL}/api/documents/{did}/reocr",
                               headers=auth_headers, timeout=30)
            assert r2.status_code == 402, r2.text
            assert r2.json().get("detail", "").startswith("Pack annonce premium requis (49 €)"), r2.text
        finally:
            r3 = requests.delete(f"{BASE_URL}/api/documents/{did}",
                                 headers=auth_headers, timeout=20)
            assert r3.status_code == 200, r3.text
            assert r3.json().get("deleted") is True, r3.text

    def test_photo_retouch_402(self, auth_headers, small_jpeg):
        # If a photo exists we reuse it; otherwise upload one, hit retouch, then delete.
        r = requests.get(f"{BASE_URL}/api/properties/{LOCKED_PID}/photos",
                         headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        existing = r.json()

        created_pid = None
        if existing:
            photo_id = existing[0].get("id") or existing[0].get("_id")
        else:
            files = {"file": ("photo.jpg", small_jpeg, "image/jpeg")}
            up = requests.post(f"{BASE_URL}/api/properties/{LOCKED_PID}/photos",
                               headers=auth_headers, files=files, timeout=30)
            assert up.status_code == 201, up.text
            created = up.json()
            photo_id = created.get("id") or created.get("_id")
            created_pid = photo_id
        assert photo_id, "no photo_id resolved"

        try:
            rt = requests.post(f"{BASE_URL}/api/photos/{photo_id}/retouch",
                               headers=auth_headers, timeout=30)
            assert rt.status_code == 402, rt.text
            assert rt.json().get("detail", "").startswith("Pack annonce premium requis (49 €)"), rt.text
        finally:
            if created_pid:
                dr = requests.delete(f"{BASE_URL}/api/photos/{created_pid}",
                                     headers=auth_headers, timeout=20)
                assert dr.status_code == 200, dr.text


# ---------------- PDF branding ----------------

class TestPdfBranding:
    def test_report_pdf_branding(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/properties/{LOCKED_PID}/report.pdf",
                         headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
        pdf_bytes = r.content
        assert pdf_bytes[:5] == b"%PDF-", pdf_bytes[:16]

        # Extract text + image count from page 1
        try:
            from pypdf import PdfReader
        except ImportError:  # pragma: no cover
            from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(pdf_bytes))
        page1 = reader.pages[0]
        text1 = (page1.extract_text() or "").replace("\n", " ")
        assert "Achètes ma maison" in text1, text1[:400]
        assert "Rapport d’estimation" in text1 or "Rapport d'estimation" in text1, text1[:400]

        # Page 1 must contain an image (logo). pypdf exposes .images
        try:
            images = list(page1.images)
        except Exception:  # noqa: BLE001
            images = []
        assert images, "no image on page 1 of report.pdf (logo expected)"

        # No stray 'Estimo' brand name anywhere in the extracted text of all pages
        all_text = " ".join((p.extract_text() or "") for p in reader.pages)
        assert "Estimo" not in all_text, all_text[:600]

    def test_notaire_pdf_ok(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/properties/{LOCKED_PID}/notaire.pdf",
                         headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"


# ---------------- Unlocked property regression (pack.pdf) ----------------

class TestUnlockedRegression:
    def test_pack_pdf_on_unlocked(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/properties", headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        props = r.json()
        unlocked_id = None
        for p in props:
            pid = p.get("id") or p.get("_id")
            if not pid:
                continue
            s = requests.get(f"{BASE_URL}/api/properties/{pid}/pack/status",
                             headers=auth_headers, timeout=15)
            if s.status_code == 200 and s.json().get("unlocked"):
                unlocked_id = pid
                break
        if not unlocked_id:
            pytest.skip("No unlocked property available in test database")

        r = requests.get(f"{BASE_URL}/api/properties/{unlocked_id}/pack.pdf",
                         headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
