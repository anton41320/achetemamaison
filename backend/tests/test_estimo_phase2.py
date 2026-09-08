"""Estimo backend API tests — Phase 2 (hedonic model, trend, PDF report)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

BLOIS_APT = {
    "address_label": "TEST P2 rue Denis Papin 41000 Blois",
    "lat": 47.586414, "lon": 1.335664, "code_commune": "41018",
    "commune": "Blois", "postcode": "41000",
    "property_type": "appartement", "surface": 65, "rooms": 3, "bedrooms": 2,
    "year_built": 1985, "condition": "correct", "land_surface": None,
}
BLOIS_HOUSE = {
    "address_label": "TEST P2 Maison Blois",
    "lat": 47.586414, "lon": 1.335664, "code_commune": "41018",
    "commune": "Blois", "postcode": "41000",
    "property_type": "maison", "surface": 110, "rooms": 5, "bedrooms": 3,
    "year_built": 1970, "condition": "bon", "land_surface": 450,
}


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# --- Hedonic model summary ---
class TestHedonicModel:
    def test_model_available(self, s):
        r = s.get(f"{API}/models/hedonic", timeout=20)
        assert r.status_code == 200
        b = r.json()
        assert b["available"] is True
        assert b["n"] > 100_000, f"expected n>100k, got {b['n']}"
        # ~110213 mentioned in requirements
        assert 100_000 < b["n"] < 200_000
        assert b["ref_year"] == 2025
        coefs = b["coefficients"]
        assert 0.6 < coefs["log_surface"] < 1.0, f"log_surface elasticity out of range: {coefs['log_surface']}"
        # in-sample & holdout metrics
        ins = b["in_sample"]
        for k in ("mape", "median_ape", "within_15pct", "r2_log", "n"):
            assert k in ins
        ho = b["holdout"]
        assert ho is not None
        assert ho.get("test_year") == 2025
        assert "median_ape" in ho

    def test_train_endpoint_kicks_off(self, s):
        r = s.post(f"{API}/models/hedonic/train", timeout=15)
        assert r.status_code == 202
        b = r.json()
        # Either just started, or already running (returns started=False with message)
        assert "started" in b
        # Poll model availability within ~15s
        deadline = time.time() + 20
        while time.time() < deadline:
            g = s.get(f"{API}/models/hedonic", timeout=15).json()
            if g["available"] and not g["training"]:
                break
            time.sleep(1)
        final = s.get(f"{API}/models/hedonic", timeout=15).json()
        assert final["available"] is True


# --- Hedonic result on property creation ---
def _check_hedonic(prop, ptype: str, expect_land: bool = False, expect_year: bool = False):
    est = prop["estimation"]
    hed = est.get("hedonic")
    assert hed is not None, "hedonic must be present"
    for k in ("value", "low", "high", "price_m2", "reference_value", "factors",
              "delta_vs_comparables_pct", "agreement", "model_version"):
        assert k in hed, f"missing {k} in hedonic"
    assert hed["low"] < hed["value"] < hed["high"]
    assert hed["price_m2"] > 0
    assert hed["agreement"] in ("convergent", "ecart_modere", "divergent")
    keys = [f["key"] for f in hed["factors"]]
    for required in ("location", "surface", "rooms", "condition"):
        assert required in keys, f"missing factor {required}, got {keys}"
    if expect_land:
        assert "land" in keys, f"maison must have land factor, got {keys}"
    else:
        assert "land" not in keys, f"appartement must NOT have land factor, got {keys}"
    if expect_year:
        assert "year" in keys, f"missing year factor, got {keys}"


class TestPropertyHedonic:
    created_ids: list = []

    def test_create_appartement_with_hedonic(self, s):
        r = s.post(f"{API}/properties", json=BLOIS_APT, timeout=60)
        assert r.status_code == 201, r.text
        prop = r.json()
        _check_hedonic(prop, "appartement", expect_land=False, expect_year=True)
        TestPropertyHedonic.created_ids.append(prop["id"])

    def test_create_maison_with_hedonic_land(self, s):
        r = s.post(f"{API}/properties", json=BLOIS_HOUSE, timeout=60)
        assert r.status_code == 201, r.text
        prop = r.json()
        _check_hedonic(prop, "maison", expect_land=True, expect_year=True)
        TestPropertyHedonic.created_ids.append(prop["id"])

    def test_reestimate_fills_hedonic(self, s):
        pid = TestPropertyHedonic.created_ids[0]
        r = s.post(f"{API}/properties/{pid}/reestimate", timeout=60)
        assert r.status_code == 200
        _check_hedonic(r.json(), "appartement", expect_land=False, expect_year=True)

    @classmethod
    def teardown_class(cls):
        sess = requests.Session()
        for pid in cls.created_ids:
            try:
                sess.delete(f"{API}/properties/{pid}", timeout=15)
            except Exception:
                pass


# --- Trend endpoint ---
class TestTrend:
    EXISTING_ID = "6aa02db9efd8f90925a5a758"

    def test_trend_shape(self, s):
        r = s.get(f"{API}/properties/{self.EXISTING_ID}/trend", timeout=30)
        assert r.status_code == 200
        b = r.json()
        assert b["years"] == [2021, 2022, 2023, 2024, 2025]
        for series_key in ("commune_series", "quartier_series"):
            series = b[series_key]
            assert len(series) == 5, f"{series_key} must have 5 points"
            years_in = [p["year"] for p in series]
            assert years_in == [2021, 2022, 2023, 2024, 2025]
            for p in series:
                assert "count" in p
                assert "median_pm2" in p
                assert isinstance(p["count"], int)
                assert p["median_pm2"] is None or isinstance(p["median_pm2"], (int, float))
        for k in ("commune_change_pct", "quartier_change_pct"):
            v = b[k]
            assert v is None or isinstance(v, (int, float))

    def test_trend_404_unknown(self, s):
        r = s.get(f"{API}/properties/000000000000000000000000/trend", timeout=15)
        assert r.status_code == 404


# --- PDF report ---
class TestReport:
    EXISTING_ID = "6aa02db9efd8f90925a5a758"

    def test_report_ok(self, s):
        r = s.get(f"{API}/properties/{self.EXISTING_ID}/report.pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 3000, f"expected >3KB, got {len(r.content)}"
        assert r.content[:5] == b"%PDF-", f"missing PDF magic, got {r.content[:8]}"

    def test_report_404_unknown(self, s):
        r = s.get(f"{API}/properties/000000000000000000000000/report.pdf", timeout=15)
        assert r.status_code == 404
