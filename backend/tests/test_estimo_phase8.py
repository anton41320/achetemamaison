"""Phase 8 backend tests — estimation range width fix (comparables_dvf_v2).

Bug being verified: previous range for maison 140 m² at 15 Rue de l'Aubier 41200
Villefranche-sur-Cher was 142 k€ – 332 k€ (±40 %). The v2 engine must:
- return method == 'comparables_dvf_v2';
- keep half-width ≤ 15 % if confidence in {eleve, moyen};
- keep half-width ≤ 20 % if confidence == 'faible';
- half-width ≥ 25 % only if insufficient_data == True;
- ensure low/high multiples of 1000 and price_m2 = round(value/surface, 10).
Also verifies auto-refresh of stored v1 estimations on GET /api/properties/{pid}.
"""
from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
PID_SEED = "6aa02db9efd8f90925a5a758"
BAD_PID = "6aa02db9efd8f90925a5a759"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _half_width(d: dict) -> float:
    return (d["high"] - d["low"]) / (2 * d["value"])


def _assert_cap(d: dict, ctx: str = ""):
    hw = _half_width(d)
    conf = d["confidence"]["level"]
    insufficient = d.get("insufficient_data", False)
    # Allow a small tolerance because low/high are rounded to the nearest 1000
    # after the theoretical cap is applied — for a ~130 k€ value this can push
    # the observed half-width up to ~0.4 % above the internal cap.
    if insufficient:
        assert hw >= 0.24, f"{ctx} expected wide range when insufficient_data (hw={hw:.3f})"
    else:
        if conf in ("eleve", "moyen"):
            assert hw <= 0.155, f"{ctx} half-width {hw:.4f} > 0.155 for conf={conf}"
        elif conf == "faible":
            assert hw <= 0.205, f"{ctx} half-width {hw:.4f} > 0.205 for conf={conf}"
    assert d["low"] < d["value"] < d["high"], f"{ctx} ordering low<value<high broken"
    # multiples of 1000
    assert d["low"] % 1000 == 0, f"{ctx} low not multiple of 1000: {d['low']}"
    assert d["high"] % 1000 == 0, f"{ctx} high not multiple of 1000: {d['high']}"
    assert d["value"] % 1000 == 0, f"{ctx} value not multiple of 1000: {d['value']}"


def _assert_price_m2(d: dict, surface: float, ctx: str = ""):
    # price_m2 is computed from the unrounded value before rounding to 1000;
    # tolerate ~10€ drift vs. round(returned_value/surface, 10).
    expected = round((d["value"] / surface) / 10) * 10
    assert abs(d["price_m2"] - expected) <= 20, (
        f"{ctx} price_m2 {d['price_m2']} vs round({d['value']}/{surface},10)={expected}")


# ---------------- POST /api/estimate/preview ----------------

class TestPreviewVillefranche:
    """The exact user-reported case."""

    payload = {
        "address_label": "15 Rue de l'Aubier 41200 Villefranche-sur-Cher",
        "lat": 47.30566, "lon": 1.763254,
        "code_commune": "41280", "commune": "Villefranche-sur-Cher", "postcode": "41200",
        "property_type": "maison", "surface": 140, "rooms": 6, "bedrooms": 4,
        "condition": "correct", "land_surface": 800,
    }

    def test_preview_method_and_shape(self, s):
        r = s.post(f"{BASE_URL}/api/estimate/preview", json=self.payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["method"] == "comparables_dvf_v2", f"method={d['method']}"
        assert "confidence" in d and "score" in d["confidence"]
        assert isinstance(d.get("notes"), list)
        _assert_cap(d, "Villefranche")
        _assert_price_m2(d, self.payload["surface"], "Villefranche")

    def test_preview_expected_range(self, s):
        r = s.post(f"{BASE_URL}/api/estimate/preview", json=self.payload, timeout=30)
        d = r.json()
        # Expected around 177k (152k–201k). Loose bounds to avoid flakiness.
        assert 150000 <= d["value"] <= 210000, f"unexpected value {d['value']}"
        assert _half_width(d) <= 0.15, f"half-width {_half_width(d):.4f} exceeds 15%"


class TestPreviewOtherCases:
    CASES = [
        {
            "name": "appartement_65_blois",
            "payload": {
                "address_label": "Blois centre", "lat": 47.5861, "lon": 1.3359,
                "code_commune": "41018", "commune": "Blois", "postcode": "41000",
                "property_type": "appartement", "surface": 65, "rooms": 3, "bedrooms": 2,
                "condition": "correct",
            },
            "surface": 65,
        },
        {
            "name": "maison_120_soings",
            "payload": {
                "address_label": "Soings-en-Sologne", "lat": 47.4137, "lon": 1.5253,
                "code_commune": "41248", "commune": "Soings-en-Sologne", "postcode": "41230",
                "property_type": "maison", "surface": 120, "rooms": 5, "bedrooms": 3,
                "condition": "correct", "year_built": 1990, "land_surface": 1200,
            },
            "surface": 120,
        },
        {
            "name": "maison_90_a_renover",
            "payload": {
                "address_label": "Soings-en-Sologne", "lat": 47.4137, "lon": 1.5253,
                "code_commune": "41248", "commune": "Soings-en-Sologne", "postcode": "41230",
                "property_type": "maison", "surface": 90, "rooms": 4, "bedrooms": 3,
                "condition": "a_renover", "land_surface": 800,
            },
            "surface": 90,
        },
    ]

    @pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
    def test_preview_case(self, s, case):
        r = s.post(f"{BASE_URL}/api/estimate/preview", json=case["payload"], timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["method"] == "comparables_dvf_v2"
        _assert_cap(d, case["name"])
        _assert_price_m2(d, case["surface"], case["name"])


# ---------------- Auto-refresh on GET /properties/{pid} ----------------

class TestAutoRefreshV2:
    def test_all_properties_are_v2_after_get(self, s):
        r = s.get(f"{BASE_URL}/api/properties", timeout=30)
        assert r.status_code == 200
        props = r.json()
        assert props, "no seed properties"
        for p in props:
            pid = p["id"]
            r2 = s.get(f"{BASE_URL}/api/properties/{pid}", timeout=45)
            assert r2.status_code == 200, r2.text
            est = r2.json()["estimation"]
            assert est["method"] == "comparables_dvf_v2", f"{pid} method={est['method']}"
            _assert_cap(est, f"prop {pid}")

    def test_reestimate_returns_v2(self, s):
        r = s.post(f"{BASE_URL}/api/properties/{PID_SEED}/reestimate", timeout=45)
        assert r.status_code == 200, r.text
        est = r.json()["estimation"]
        assert est["method"] == "comparables_dvf_v2"
        _assert_cap(est, "reestimate seed")


# ---------------- /api/validation still works ----------------

class TestValidation:
    def test_validation_n40(self, s):
        r = s.get(f"{BASE_URL}/api/validation", params={"n": 40}, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("n", "mape", "median_ape", "coverage"):
            assert k in data, f"missing {k} in {list(data)}"


# ---------------- Regression: existing PDFs / endpoints ----------------

class TestRegression:
    def test_final(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID_SEED}/final", timeout=30)
        assert r.status_code == 200
        assert r.json()["value"] > 0

    def test_target(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID_SEED}/target", timeout=30)
        assert r.status_code == 200

    def test_report_pdf(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID_SEED}/report.pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

    def test_notaire_pdf(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{PID_SEED}/notaire.pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
