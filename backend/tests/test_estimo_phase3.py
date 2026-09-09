"""Estimo backend API tests — Phase 3 (ML, blended final, market signal, listings)."""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
EXISTING_ID = "6aa02db9efd8f90925a5a758"


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# --- ML model meta ---
class TestMlModel:
    def test_ml_meta(self, s):
        r = s.get(f"{API}/models/ml", timeout=20)
        assert r.status_code == 200
        b = r.json()
        assert b["available"] is True
        assert b["promoted"] is False, f"expected NOT promoted (baseline still wins), got {b.get('promoted')}"
        ho = b.get("holdout")
        assert ho and "median_ape" in ho and ho.get("test_year") == 2025
        gate = b.get("gate")
        assert gate, "gate metrics missing"
        assert 250 <= gate.get("n", 0) <= 400, f"gate n≈300, got {gate.get('n')}"
        assert "ml_median_ape" in gate and "baseline_median_ape" in gate
        # baseline should beat ml per spec (21.7 vs 18.1)
        assert gate["baseline_median_ape"] <= gate["ml_median_ape"]
        fi = b.get("feature_importance")
        assert fi and (isinstance(fi, dict) or isinstance(fi, list)) and len(fi) > 0


# --- Reestimate returns ml + market_estimate ---
class TestReestimate:
    def test_reestimate_has_ml_and_market(self, s):
        r = s.post(f"{API}/properties/{EXISTING_ID}/reestimate", timeout=90)
        assert r.status_code == 200, r.text
        est = r.json()["estimation"]
        ml = est.get("ml")
        assert ml is not None, "estimation.ml must be present"
        assert ml["promoted"] is False
        assert ml["low"] < ml["value"] < ml["high"]
        keys = [f["key"] for f in ml["factors"]]
        # per spec expects at least location + surface family
        assert "location" in keys and "surface" in keys, f"unexpected ml factor keys: {keys}"
        me = est.get("market_estimate")
        assert me is not None and me["value"] > 0 and me["count"] > 0 and me["label"]


# --- Weights CRUD ---
class TestWeights:
    def test_get_defaults_shape(self, s):
        r = s.get(f"{API}/settings/weights", timeout=15)
        assert r.status_code == 200
        b = r.json()
        for k in ("comparables", "hedonic", "market", "ml"):
            assert k in b

    def test_put_persists(self, s):
        payload = {"comparables": 60, "hedonic": 20, "market": 20, "ml": 0}
        r = s.put(f"{API}/settings/weights", json=payload, timeout=15)
        assert r.status_code == 200
        g = s.get(f"{API}/settings/weights", timeout=15).json()
        assert g == payload

    def test_all_zero_rejected(self, s):
        r = s.put(f"{API}/settings/weights", json={"comparables": 0, "hedonic": 0, "market": 0, "ml": 0}, timeout=15)
        assert r.status_code == 422

    def test_out_of_range_rejected(self, s):
        r = s.put(f"{API}/settings/weights", json={"comparables": 150, "hedonic": 20, "market": 20, "ml": 0}, timeout=15)
        assert r.status_code == 422

    def test_restore_defaults(self, s):
        r = s.put(f"{API}/settings/weights",
                  json={"comparables": 50, "hedonic": 30, "market": 20, "ml": 0}, timeout=15)
        assert r.status_code == 200


# --- Blended final ---
class TestFinal:
    def test_final_shape(self, s):
        r = s.get(f"{API}/properties/{EXISTING_ID}/final", timeout=30)
        assert r.status_code == 200
        b = r.json()
        for k in ("value", "low", "high", "components", "weights"):
            assert k in b
        assert b["low"] <= b["value"] <= b["high"]
        comps = b["components"]
        assert len(comps) == 4
        keys = {c["key"] for c in comps}
        assert keys == {"comparables", "hedonic", "market", "ml"}
        ml_comp = next(c for c in comps if c["key"] == "ml")
        assert ml_comp["effective_weight"] == 0.0, "ml should not contribute (not promoted)"
        active = [c for c in comps if c["available"] and c["effective_weight"] > 0]
        total = sum(c["effective_weight"] for c in active)
        assert abs(total - 1.0) < 0.01, f"effective weights should sum to 1, got {total}"
        # coherence: value is within [min low, max high] of active components
        assert b["value"] >= min(c["low"] for c in active) - 5000
        assert b["value"] <= max(c["high"] for c in active) + 5000


# --- Market signal ---
class TestMarketSignal:
    def test_shape(self, s):
        r = s.get(f"{API}/properties/{EXISTING_ID}/market-signal", timeout=30)
        assert r.status_code == 200
        b = r.json()
        assert b["available"] is True
        assert 0 <= b["score"] <= 100
        assert b["verdict"] in ("favorable", "neutre", "attentiste")
        assert isinstance(b.get("as_of"), str)
        reasons = b["reasons"]
        assert len(reasons) == 3
        rkeys = [r_["key"] for r_ in reasons]
        assert rkeys == ["trend", "volume", "liquidity"]


# --- Listings (LLM) ---
class TestListings:
    created_lid = None

    def test_invalid_style(self, s):
        r = s.post(f"{API}/properties/{EXISTING_ID}/listings",
                   json={"style": "bogus", "extra_facts": None, "include_price": True}, timeout=15)
        assert r.status_code == 422

    def test_unknown_property(self, s):
        r = s.post(f"{API}/properties/000000000000000000000000/listings",
                   json={"style": "sobre", "include_price": True}, timeout=15)
        assert r.status_code == 404

    def test_create_and_list(self, s):
        t0 = time.time()
        r = s.post(f"{API}/properties/{EXISTING_ID}/listings",
                   json={"style": "sobre", "extra_facts": "garage attenant", "include_price": True},
                   timeout=90)
        elapsed = time.time() - t0
        assert r.status_code == 201, f"got {r.status_code}: {r.text}"
        b = r.json()
        assert b["title"] and b["hook"] and b["description"]
        assert isinstance(b["highlights"], list) and len(b["highlights"]) >= 3
        assert b["model"] == "claude-sonnet-4-6"
        # French content sanity: at least one common french word/char
        combined = (b["title"] + " " + b["description"]).lower()
        assert any(ch in combined for ch in ("é", "è", "à", "ê")) or " le " in combined or " la " in combined
        TestListings.created_lid = b["id"]
        print(f"listing generated in {elapsed:.1f}s")

        lst = s.get(f"{API}/properties/{EXISTING_ID}/listings", timeout=15).json()
        assert any(item["id"] == b["id"] for item in lst)

    def test_delete(self, s):
        assert TestListings.created_lid, "must have a created listing"
        r = s.delete(f"{API}/properties/{EXISTING_ID}/listings/{TestListings.created_lid}", timeout=15)
        assert r.status_code == 200
        lst = s.get(f"{API}/properties/{EXISTING_ID}/listings", timeout=15).json()
        assert not any(item["id"] == TestListings.created_lid for item in lst)


# --- PDF still OK ---
class TestPdf:
    def test_pdf_ok(self, s):
        r = s.get(f"{API}/properties/{EXISTING_ID}/report.pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
