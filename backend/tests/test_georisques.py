"""Iteration 19 — Géorisques integration.

Backend coverage:
- GET /api/properties/{id}/risks (auth, 404 on missing, cache speed, refresh=true)
- GET /api/properties/{id}/dossier (risks non null, ERP required, geotechnique required for maison in zone argile 2)
- GET /api/properties/{id}/report.pdf and /notaire.pdf contain the « Risques & environnement » section
"""
from __future__ import annotations

import io
import os
import time

import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"
PROP_ID = "6aa3f68d440f04920cdaffde"
FAKE_ID = "000000000000000000000000"


# ── shared fixtures ────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def token() -> str:
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, r.text
    return tok


@pytest.fixture(scope="module")
def auth(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Géorisques risks endpoint ──────────────────────────────────────────────────
class TestRisksEndpoint:
    def test_risks_unauthenticated(self):
        r = requests.get(f"{API}/properties/{PROP_ID}/risks", timeout=15)
        assert r.status_code == 401, r.status_code

    def test_risks_ok_and_shape(self, auth):
        r = requests.get(f"{API}/properties/{PROP_ID}/risks", headers=auth, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("fetched_at", "partial", "source_url", "items", "argile", "radon", "catnat", "icpe", "dossier_flags"):
            assert k in d, f"missing {k}"
        assert "georisques" in d["source_url"].lower()
        assert isinstance(d["partial"], bool)
        # items
        assert isinstance(d["items"], list)
        for it in d["items"][:1]:
            for k in ("key", "label", "family", "present", "scope", "level"):
                assert k in it
            assert it["scope"] in ("adresse", "commune")
            assert it["level"] in ("none", "low", "medium", "high", "info")
        # argile expected exposition moyenne on this property
        assert d["argile"]["code"] == "2", f"argile.code={d['argile']!r} (partial={d['partial']})"
        assert d["argile"]["level"] == "medium"
        assert "moyenne" in d["argile"]["label"].lower()
        # radon shape
        for k in ("code", "level", "label"):
            assert k in d["radon"]
        # catnat count expected >= 1
        assert d["catnat"]["count"] >= 1, f"catnat={d['catnat']!r} (partial={d['partial']})"
        assert isinstance(d["catnat"]["by_type"], dict)
        assert isinstance(d["catnat"]["last"], list)
        # icpe
        assert "count" in d["icpe"] and "radius_m" in d["icpe"] and "sites" in d["icpe"]
        # dossier flags
        f = d["dossier_flags"]
        assert f["erp_required"] is True
        assert f["geotechnique_required"] is True

    def test_risks_cache_is_fast(self, auth):
        # second call must hit the cache and be < 1 s
        t0 = time.perf_counter()
        r = requests.get(f"{API}/properties/{PROP_ID}/risks", headers=auth, timeout=10)
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200
        assert elapsed < 1.0, f"cache too slow: {elapsed:.2f}s"

    def test_risks_refresh(self, auth):
        # refresh must succeed, tolerate up to 30 s and partial=true (external API is flaky)
        t0 = time.perf_counter()
        r = requests.get(f"{API}/properties/{PROP_ID}/risks?refresh=true", headers=auth, timeout=40)
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200, r.text
        assert elapsed <= 35, f"refresh too slow: {elapsed:.2f}s"
        d = r.json()
        assert "items" in d
        # Do not fail if partial=True (documented tolerance)

    def test_risks_404_on_missing(self, auth):
        r = requests.get(f"{API}/properties/{FAKE_ID}/risks", headers=auth, timeout=15)
        assert r.status_code == 404, r.status_code


# ── Dossier checklist adjusted by Géorisques ───────────────────────────────────
class TestDossierRisks:
    def test_dossier_contains_risks_and_flags(self, auth):
        r = requests.get(f"{API}/properties/{PROP_ID}/dossier", headers=auth, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("risks") is not None, "dossier.risks must not be null when Géorisques is available"
        items = {it["key"]: it for it in d["items"]}
        # ERP always required + reason starts with 'Toujours requis ·'
        assert "erp" in items
        assert items["erp"]["required"] is True
        assert items["erp"]["reason"].startswith("Toujours requis ·"), items["erp"]["reason"]
        # Geotechnique required (argile 2) + reason contains Géorisques
        assert "geotechnique" in items, "geotechnique item missing"
        assert items["geotechnique"]["required"] is True
        assert "Géorisques" in items["geotechnique"]["reason"], items["geotechnique"]["reason"]


# ── PDFs contain the Risques section ───────────────────────────────────────────
def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def _pdf_page_text(content: bytes, page_index: int) -> str:
    reader = PdfReader(io.BytesIO(content))
    return reader.pages[page_index].extract_text() or ""


class TestPdfsRisks:
    def test_report_pdf_contains_risks_section(self, auth):
        r = requests.get(f"{API}/properties/{PROP_ID}/report.pdf", headers=auth, timeout=60)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        text = _pdf_text(r.content)
        assert "Risques & environnement (G" in text, "expected 'Risques & environnement (Géorisques)' in report"
        assert "orisques" in text  # cover UTF-8 extraction quirks

    def test_notaire_pdf_first_page_contains_risks(self, auth):
        r = requests.get(f"{API}/properties/{PROP_ID}/notaire.pdf", headers=auth, timeout=60)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        page1 = _pdf_page_text(r.content, 0)
        assert "Risques & environnement" in page1, f"page1 must contain 'Risques & environnement'. Got: {page1[:400]}"
