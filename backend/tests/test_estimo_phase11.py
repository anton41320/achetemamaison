"""Iteration 12 review — pack live-readiness flags, receipt email exposure, report photos page."""
from __future__ import annotations

import io
import os

import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PAID_PID = "6aa02db9efd8f90925a5a758"  # already unlocked from iteration 11


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------- Pack status: live-readiness + receipt fields ----------------

class TestPackStatus:
    def test_pack_status_shape_and_flags(self, api_client):
        r = api_client.get(f"{API}/properties/{PAID_PID}/pack/status")
        assert r.status_code == 200, r.text
        d = r.json()
        # live-readiness flags
        assert d["mode"] == "test", f"expected mode 'test', got {d.get('mode')}"
        assert d["webhook_configured"] is False
        assert d["email_ready"] is True, "EMERGENT_EMAIL_KEY must be configured"
        assert d["payments_available"] is True
        assert d["unlocked"] is True, "seed pid should already be unlocked"
        # last_order shape — keys must be present
        lo = d.get("last_order")
        assert lo is not None
        for k in ("customer_email", "receipt_sent", "paid_at"):
            assert k in lo, f"missing last_order.{k}"


# ---------------- Report PDF with/without photos page ----------------

class TestReportPdf:
    def test_report_pdf_with_photos_has_photos_page(self, api_client):
        r = api_client.get(f"{API}/properties/{PAID_PID}/report.pdf")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        reader = PdfReader(io.BytesIO(r.content))
        n = len(reader.pages)
        assert n == 3, f"expected 3 pages with photos, got {n}"
        full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
        assert "Photos du bien" in full_text, "missing 'Photos du bien' heading"
        assert "non contractuel" in full_text, "missing 'non contractuel' disclaimer"

    def test_report_pdf_without_photos(self, api_client):
        r = api_client.get(f"{API}/properties/{PAID_PID}/report.pdf", params={"photos": "false"})
        assert r.status_code == 200, r.text
        reader = PdfReader(io.BytesIO(r.content))
        n = len(reader.pages)
        assert n == 2, f"expected 2 pages without photos, got {n}"
        full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
        assert "Photos du bien" not in full_text, "photos page should not be present"


# ---------------- Stripe webhook — invalid signature ----------------

class TestStripeWebhook:
    def test_webhook_without_signature_returns_400(self, api_client):
        r = api_client.post(f"{API}/stripe/webhook", data=b"{}", headers={"Content-Type": "application/json"})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


# ---------------- Regressions ----------------

class TestRegressions:
    def test_pack_pdf_paid_property(self, api_client):
        # Listings may be generated on the fly with the LLM — acceptable once
        r = api_client.get(f"{API}/properties/{PAID_PID}/pack.pdf", timeout=90)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")

    def test_next_steps(self, api_client):
        r = api_client.get(f"{API}/next-steps")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "properties" in data

    def test_list_properties(self, api_client):
        r = api_client.get(f"{API}/properties")
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) > 0
