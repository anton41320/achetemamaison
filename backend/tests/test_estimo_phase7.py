"""Phase 7 backend tests — Target price, Alerts, Notaire export."""
from __future__ import annotations

import io
import os

import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
PID = "6aa02db9efd8f90925a5a758"
DPE_DOC_ID = "6aa14d4e4e0e34732207382f"
BAD_PID = "6aa02db9efd8f90925a5a759"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------------- Target price ----------------

class TestTargetPrice:
    def test_get_target_initial(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID}/target", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "target_price" in data
        assert "analysis" in data
        # seed sets 250000
        assert data["target_price"] == 250000
        a = data["analysis"]
        assert a is not None
        for k in ("zone", "label", "advice", "tips", "position", "delta_pct",
                 "net_after_negotiation", "low", "high", "value"):
            assert k in a, f"missing {k}"
        assert a["zone"] in {"sous_fourchette", "bas", "central", "haut", "au_dessus"}
        assert isinstance(a["tips"], list) and len(a["tips"]) > 0

    def test_property_target_field_present(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID}", timeout=20)
        assert r.status_code == 200
        assert "target_price" in r.json()

    def test_estimation_unchanged_by_target_put(self, s):
        before = s.get(f"{BASE_URL}/api/properties/{PID}", timeout=20).json()["estimation"]["value"]
        r = s.put(f"{BASE_URL}/api/properties/{PID}/target", json={"target_price": 250000}, timeout=30)
        assert r.status_code == 200, r.text
        after = s.get(f"{BASE_URL}/api/properties/{PID}", timeout=20).json()["estimation"]["value"]
        assert before == after

    def test_put_target_valid_returns_analysis(self, s):
        r = s.put(f"{BASE_URL}/api/properties/{PID}/target", json={"target_price": 250000}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["target_price"] == 250000
        assert data["analysis"] is not None
        assert data["analysis"]["zone"] in {"sous_fourchette", "bas", "central", "haut", "au_dessus"}
        assert data["analysis"]["net_after_negotiation"] > 0

    def test_put_target_null_clears(self, s):
        r = s.put(f"{BASE_URL}/api/properties/{PID}/target", json={"target_price": None}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["target_price"] is None
        assert data["analysis"] is None
        # restore
        s.put(f"{BASE_URL}/api/properties/{PID}/target", json={"target_price": 250000}, timeout=30)

    def test_put_target_too_low_422(self, s):
        r = s.put(f"{BASE_URL}/api/properties/{PID}/target", json={"target_price": 500}, timeout=20)
        assert r.status_code == 422

    def test_put_target_unknown_pid_404(self, s):
        r = s.put(f"{BASE_URL}/api/properties/{BAD_PID}/target", json={"target_price": 250000}, timeout=20)
        assert r.status_code == 404


# ---------------- Alerts ----------------

class TestAlerts:
    def test_alerts_shape(self, s):
        r = s.get(f"{BASE_URL}/api/alerts", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "as_of" in data and "horizon_days" in data and "alerts" in data
        assert data["horizon_days"] == 90
        assert isinstance(data["alerts"], list)
        # Should include the DPE alert for our seed property
        for a in data["alerts"]:
            for k in ("property_id", "address_label", "document_id", "item_key",
                     "label", "expiry_date", "days_left", "level"):
                assert k in a
            assert a["level"] in {"expire", "urgent", "bientot"}

    def test_alert_contains_dpe(self, s):
        r = s.get(f"{BASE_URL}/api/alerts", timeout=20)
        alerts = r.json()["alerts"]
        dpe = [a for a in alerts if a["property_id"] == PID and a["document_id"] == DPE_DOC_ID]
        assert len(dpe) == 1, f"expected DPE alert for {PID}, got {alerts}"
        # ~40 days at server clock 2026-09-10 (expiry 2026-10-20)
        assert 30 < dpe[0]["days_left"] < 60

    def test_horizon_days_excludes_far_alerts(self, s):
        r = s.get(f"{BASE_URL}/api/alerts", params={"horizon_days": 10}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["horizon_days"] == 10
        for a in data["alerts"]:
            assert a["days_left"] <= 10
        # DPE ~40 days should be excluded
        assert not any(a["document_id"] == DPE_DOC_ID for a in data["alerts"])


# ---------------- Notaire PDF export ----------------

class TestNotaire:
    def test_notaire_pdf_ok(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID}/notaire.pdf", timeout=60)
        assert r.status_code == 200, r.text[:400]
        assert r.headers["content-type"].startswith("application/pdf")
        pdf = PdfReader(io.BytesIO(r.content))
        assert len(pdf.pages) >= 3, f"expected ≥3 pages, got {len(pdf.pages)}"
        text = pdf.pages[0].extract_text() or ""
        assert "Dossier de vente" in text, f"cover missing title, got: {text[:300]}"
        assert "Pièces jointes" in text
        # Prix cible present since target=250000
        assert "Prix cible" in text or "cible" in text.lower()

    def test_notaire_unknown_pid_404(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{BAD_PID}/notaire.pdf", timeout=20)
        assert r.status_code == 404

    def test_notaire_works_for_property_without_docs(self, s):
        # find another property with no validated docs
        props = s.get(f"{BASE_URL}/api/properties", timeout=20).json()
        other = next((p for p in props if p["id"] != PID), None)
        if not other:
            pytest.skip("no second property to test")
        r = s.get(f"{BASE_URL}/api/properties/{other['id']}/notaire.pdf", timeout=60)
        assert r.status_code == 200
        pdf = PdfReader(io.BytesIO(r.content))
        assert len(pdf.pages) >= 1


# ---------------- Regression ----------------

class TestRegression:
    def test_property_detail_still_estimates(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID}", timeout=20)
        assert r.status_code == 200
        assert r.json()["estimation"]["value"] > 0

    def test_final(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID}/final", timeout=20)
        assert r.status_code == 200
        assert r.json()["value"] > 0

    def test_dossier(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID}/dossier", timeout=20)
        assert r.status_code == 200
        assert "items" in r.json()
