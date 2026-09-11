"""Phase 10 backend tests: similar-size-commune widening (comparables_dvf_v4)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SEED_PID = "6aa02db9efd8f90925a5a758"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- DVF status ---
def test_dvf_status_communes_populations(s):
    r = s.get(f"{API}/dvf/status", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["communes_with_population"] > 800, data


# --- Hamlet Mur-de-Sologne: needs 10 km widening ---
def test_preview_hamlet_mur_de_sologne(s):
    payload = {
        "address_label": "Hameau", "lat": 47.45, "lon": 1.70,
        "code_commune": "41156", "commune": "Mur-de-Sologne", "postcode": "41230",
        "property_type": "maison", "surface": 200, "rooms": 7, "bedrooms": 4,
        "condition": "bon", "land_surface": 3000,
    }
    r = s.post(f"{API}/estimate/preview", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    est = r.json()
    assert est["method"] == "comparables_dvf_v4", est["method"]
    conf = est["confidence"]
    assert conf["radius_label"] == "10 km, communes similaires", conf["radius_label"]
    notes = est.get("notes") or []
    joined = " ".join(notes)
    assert "communes de taille comparable" in joined, notes
    assert "508" in joined, notes
    assert est["insufficient_data"] is False
    half = (est["high"] - est["low"]) / (2 * est["value"])
    assert half <= 0.20, half
    # population fields and size band
    lo, hi = 0.4 * 508, 2.5 * 508
    for c in est["comparables"]:
        assert isinstance(c.get("population"), int), c
        if c["commune"] != "Mur-de-Sologne":
            assert lo <= c["population"] <= hi, (c["commune"], c["population"])


# --- Villefranche 140 m²: 5 km similar-size level ---
def test_preview_villefranche(s):
    payload = {
        "address_label": "Villefranche-sur-Cher", "lat": 47.30566, "lon": 1.763254,
        "code_commune": "41280", "commune": "Villefranche-sur-Cher", "postcode": "41200",
        "property_type": "maison", "surface": 140, "rooms": 6, "bedrooms": 4,
        "condition": "correct", "land_surface": 800,
    }
    r = s.post(f"{API}/estimate/preview", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    est = r.json()
    assert est["method"] == "comparables_dvf_v4"
    assert 150000 <= est["value"] <= 200000, est["value"]
    half = (est["high"] - est["low"]) / (2 * est["value"])
    assert half <= 0.15, half
    prox = next((d for d in est["confidence"]["details"] if d["key"] == "proximity"), None)
    assert prox and "distance médiane pondérée" in prox["hint"], prox
    market_labels = [m["label"] for m in est["market"]]
    assert len(market_labels) == 4
    assert "5 km, communes similaires" in market_labels, market_labels


# --- Blois appartement: dense, stays local ---
def test_preview_blois_appt(s):
    payload = {
        "address_label": "Blois", "lat": 47.5861, "lon": 1.3359,
        "code_commune": "41018", "commune": "Blois", "postcode": "41000",
        "property_type": "appartement", "surface": 65, "rooms": 3, "bedrooms": 2,
        "condition": "correct", "land_surface": None,
    }
    r = s.post(f"{API}/estimate/preview", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    est = r.json()
    assert est["confidence"]["radius_label"] in ("À 500 m", "Quartier (1,5 km)"), est["confidence"]["radius_label"]
    for c in est["comparables"]:
        assert c["commune"] == "Blois", c


# --- Property GET auto-refresh to v4 ---
def test_property_auto_refresh_seed(s):
    r = s.get(f"{API}/properties/{SEED_PID}", timeout=60)
    assert r.status_code == 200
    p = r.json()
    est = p.get("estimation")
    assert est and est["method"] == "comparables_dvf_v4"
    assert est["comparables"], "no comparables"
    for c in est["comparables"]:
        assert "population" in c, c


def test_all_properties_method_v4(s):
    r = s.get(f"{API}/properties", timeout=60)
    assert r.status_code == 200
    props = r.json()
    if isinstance(props, dict):
        props = props.get("properties", [])
    for prop in props:
        pid = prop["id"]
        rr = s.get(f"{API}/properties/{pid}", timeout=60)
        assert rr.status_code == 200
        est = rr.json().get("estimation")
        if est:  # some properties may not have coordinates
            assert est["method"] == "comparables_dvf_v4", (pid, est["method"])
            for c in est.get("comparables", []):
                assert "population" in c


def test_regression_alerts(s):
    r = s.get(f"{API}/alerts", timeout=30)
    assert r.status_code == 200


# --- Validation ---
def test_validation_n30(s):
    t0 = time.time()
    r = s.get(f"{API}/validation", params={"n": 30}, timeout=125)
    assert r.status_code == 200, r.text
    elapsed = time.time() - t0
    assert elapsed <= 120, elapsed
    d = r.json()
    assert "n" in d


# --- Regression ---
def test_regression_final(s):
    r = s.get(f"{API}/properties/{SEED_PID}/final", timeout=30)
    assert r.status_code == 200


def test_regression_target(s):
    r = s.get(f"{API}/properties/{SEED_PID}/target", timeout=30)
    assert r.status_code == 200


def test_regression_report_pdf(s):
    r = s.get(f"{API}/properties/{SEED_PID}/report.pdf", timeout=60)
    assert r.status_code == 200


def test_regression_next_steps(s):
    r = s.get(f"{API}/properties/{SEED_PID}/next-steps", timeout=30)
    assert r.status_code == 200

