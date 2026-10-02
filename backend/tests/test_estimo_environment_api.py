"""Tests end-to-end pour la nouvelle feature environnement (POST /analyze, GET /properties/{id}/environment)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"
PROP_A = "6aa3f68d440f04920cdaffde"  # supposé déjà analysé → cached
PROP_B = "6aa02db9efd8f90925a5a758"  # première analyse


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- POST /api/analyze ----------
class TestAnalyzeEndpoint:
    def test_analyze_blois_default_radii(self, auth_headers):
        t = time.time()
        r = requests.post(f"{API}/analyze", json={"address": "1 Rue Denis Papin 41000 Blois", "report": False},
                          headers=auth_headers, timeout=90)
        dur = time.time() - t
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        assert dur < 90, f"took {dur:.1f}s"
        j = r.json()
        # location
        loc = j["location"]
        assert loc["address"].get("label"), "address.label missing"
        c = loc["coordinates"]
        assert isinstance(c["lon"], (int, float)) and isinstance(c["lat"], (int, float))
        # property
        prop = j["property"]
        assert prop["parcel"] is not None, "parcel should not be null for 1 Rue Denis Papin Blois"
        assert prop["parcel"].get("section") and prop["parcel"].get("numero")
        assert "building" in prop
        # analysis
        a = j["analysis"]
        for key in ("roads", "water", "services", "transport", "green_spaces", "nuisances",
                    "terrain", "urbanism", "rings", "radii_m", "limits", "unavailable"):
            assert key in a, f"analysis missing key: {key}"
        assert len(a["rings"]) == 4
        assert a["radii_m"] == [50, 250, 1000, 5000]
        assert isinstance(a["terrain"].get("altitude_m"), (int, float)), "terrain.altitude_m must be numeric"
        assert a["urbanism"].get("zones"), "urbanism.zones should not be empty"
        # distances / shape sur roads et services
        for coll in ("roads", "services"):
            for item in a[coll]:
                assert isinstance(item.get("distance_m"), int), f"{coll} distance_m must be int ({item})"
                assert item.get("ring"), f"{coll} missing ring"
                assert item.get("direction"), f"{coll} missing direction"
                assert item.get("source"), f"{coll} missing source"
        # sources
        srcs = j["sources"]
        assert isinstance(srcs, list) and len(srcs) >= 3
        for s in srcs:
            for k in ("id", "name", "licence", "fetched_at", "status"):
                assert k in s, f"source missing {k}: {s}"

    def test_analyze_404_unknown_address(self, auth_headers):
        r = requests.post(f"{API}/analyze", json={"address": "zzzz qsdf 00000 Nullepart", "report": False},
                          headers=auth_headers, timeout=60)
        assert r.status_code == 404, f"expected 404 got {r.status_code} {r.text[:200]}"

    def test_analyze_custom_radii(self, auth_headers):
        r = requests.post(f"{API}/analyze",
                          json={"address": "1 Rue Denis Papin 41000 Blois", "report": False,
                                "radii_m": [100, 500, 2000]},
                          headers=auth_headers, timeout=90)
        assert r.status_code == 200
        a = r.json()["analysis"]
        assert a["radii_m"] == [100, 500, 2000]
        assert len(a["rings"]) == 3


# ---------- GET /api/properties/{id}/environment ----------
class TestPropertyEnvironment:
    def test_prop_a_cached_fast(self, auth_headers):
        t = time.time()
        r = requests.get(f"{API}/properties/{PROP_A}/environment", headers=auth_headers, timeout=30)
        dur = time.time() - t
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        j = r.json()
        assert j.get("cached") is True, f"expected cached=True (prop should already be analyzed), got {j.get('cached')}"
        assert dur < 5, f"cached call too slow: {dur:.2f}s"
        assert "analysis" in j
        rep = j.get("report")
        assert rep is not None, "report missing"
        if rep.get("sections"):
            sections = rep["sections"]
            expected = {"resume", "immediat", "voisinage", "nature", "mobilite", "services",
                        "nuisances", "terrain", "risques", "urbanisme", "evolution", "a_verifier"}
            missing = expected - set(sections.keys())
            assert not missing, f"report.sections missing keys: {missing}"
            assert isinstance(sections["a_verifier"], list), "a_verifier must be a list"
        # estimation_adjustments: env_* and sum within [-0.06, 0.04]
        adj = j.get("estimation_adjustments")
        assert isinstance(adj, list) and len(adj) >= 1, f"estimation_adjustments empty: {adj}"
        assert all(a["key"].startswith("env_") for a in adj), f"all keys must start with env_: {[a['key'] for a in adj]}"
        total = sum(a["pct"] for a in adj)
        assert -0.06 - 1e-6 <= total <= 0.04 + 1e-6, f"sum pct out of bounds: {total}"

    def test_prop_a_estimation_contains_env_adjustments(self, auth_headers):
        r = requests.get(f"{API}/properties/{PROP_A}", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        est = r.json().get("estimation") or {}
        env_adj = [a for a in est.get("adjustments", []) if a["key"].startswith("env_")]
        assert env_adj, "estimation.adjustments must contain env_* entries"
        notes = est.get("notes") or []
        joined = " ".join(notes) if isinstance(notes, list) else str(notes)
        assert "environnement" in joined.lower() or "Ajustement environnement" in joined, \
            f"estimation.notes missing environnement note: {notes}"

    def test_prop_b_first_analysis_then_estimation(self, auth_headers):
        t = time.time()
        r = requests.get(f"{API}/properties/{PROP_B}/environment", headers=auth_headers, timeout=180)
        dur = time.time() - t
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        j = r.json()
        assert dur < 150, f"too slow: {dur:.1f}s"
        # cached may be False if first run OR True if previously cached in this env
        assert "analysis" in j
        rep = j.get("report")
        assert rep is not None
        # Either sections or error is acceptable (acceptable si LLM échoue mais le signaler)
        if rep.get("error"):
            print(f"[warn] LLM report failed for PROP_B: {rep.get('error')}")
        else:
            assert rep.get("sections"), "report.sections missing without error"
        # then estimation
        r2 = requests.get(f"{API}/properties/{PROP_B}", headers=auth_headers, timeout=15)
        assert r2.status_code == 200
        pdoc = r2.json()
        est = pdoc.get("estimation") or {}
        # updated_at vit au niveau du bien (pas de l'estimation)
        assert pdoc.get("updated_at"), "property.updated_at missing after reestimation"
        # vérifier env_* ajusté (facultatif selon ce que renvoie Georisques)
        env_adj = [a for a in est.get("adjustments", []) if a["key"].startswith("env_")]
        if not env_adj:
            print(f"[warn] no env_* adjustments after first analysis (acceptable si LLM/sources dégradés)")


# ---------- non-régression ----------
class TestNonRegression:
    def test_dossier_fast(self, auth_headers):
        t = time.time()
        r = requests.get(f"{API}/properties/{PROP_A}/dossier", headers=auth_headers, timeout=10)
        dur = time.time() - t
        assert r.status_code == 200
        assert dur < 2.0, f"dossier too slow: {dur:.2f}s"

    def test_reestimate_preserves_env(self, auth_headers):
        r = requests.post(f"{API}/properties/{PROP_A}/reestimate", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        est = r.json().get("estimation") or {}
        env_adj = [a for a in est.get("adjustments", []) if a["key"].startswith("env_")]
        assert env_adj, "reestimate must preserve env_* adjustments"
