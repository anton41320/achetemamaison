"""Estimo backend API tests — Phase 1 estimation engine."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# --- Health & DVF status ---
class TestHealth:
    def test_health_ok(self, s):
        r = s.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert set(body["departments"]) == {"41", "37", "45"}

    def test_dvf_status(self, s):
        r = s.get(f"{API}/dvf/status", timeout=20)
        assert r.status_code == 200
        b = r.json()
        assert b["state"] in ("idle", "running")
        assert b["total"] > 100_000, f"expected >100k DVF sales, got {b['total']}"
        depts = {d["dept"]: d for d in b["departments"]}
        for d in ("41", "37", "45"):
            assert d in depts
            assert depts[d]["total"] > 0


# --- Geocoding (BAN) ---
class TestGeocode:
    def test_geocode_covered_blois(self, s):
        r = s.get(f"{API}/geocode", params={"q": "1 rue denis papin blois"}, timeout=20)
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) > 0
        first = results[0]
        assert first["covered"] is True
        assert isinstance(first["lat"], (int, float))
        assert isinstance(first["lon"], (int, float))
        assert first["citycode"]

    def test_geocode_uncovered_paris(self, s):
        r = s.get(f"{API}/geocode", params={"q": "1 rue de rivoli paris"}, timeout=20)
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) > 0
        assert results[0]["covered"] is False


# --- Properties CRUD + estimation ---
BLOIS_APT = {
    "address_label": "TEST 1 rue Denis Papin 41000 Blois",
    "lat": 47.586414, "lon": 1.335664, "code_commune": "41018",
    "commune": "Blois", "postcode": "41000",
    "property_type": "appartement", "surface": 65, "rooms": 3, "bedrooms": 2,
    "year_built": 1985, "condition": "correct", "land_surface": None,
}

BLOIS_HOUSE = {
    "address_label": "TEST Maison Blois",
    "lat": 47.586414, "lon": 1.335664, "code_commune": "41018",
    "commune": "Blois", "postcode": "41000",
    "property_type": "maison", "surface": 110, "rooms": 5, "bedrooms": 3,
    "year_built": 1970, "condition": "bon", "land_surface": 450,
}


def _check_estimation(prop):
    est = prop["estimation"]
    assert est is not None
    assert est["low"] < est["value"] < est["high"]
    assert est["price_m2"] > 0
    conf = est["confidence"]
    assert 0 <= conf["score"] <= 100
    assert conf["level"] in ("eleve", "moyen", "faible")
    assert isinstance(est["market"], list) and len(est["market"]) == 3
    assert len(est["comparables"]) <= 30
    assert isinstance(est["adjustments"], list)


class TestProperties:
    created_ids: list = []

    def test_create_appartement(self, s):
        r = s.post(f"{API}/properties", json=BLOIS_APT, timeout=60)
        assert r.status_code == 201, r.text
        prop = r.json()
        assert prop["id"]
        _check_estimation(prop)
        TestProperties.created_ids.append(prop["id"])

    def test_create_maison_with_land_adjustment(self, s):
        r = s.post(f"{API}/properties", json=BLOIS_HOUSE, timeout=60)
        assert r.status_code == 201, r.text
        prop = r.json()
        _check_estimation(prop)
        keys = [a["key"] for a in prop["estimation"]["adjustments"]]
        assert "land" in keys, f"expected land adjustment, got {keys}"
        TestProperties.created_ids.append(prop["id"])

    def test_create_remote_widening_or_insufficient(self, s):
        # Rural address in Loiret to force radius widening / insufficient flag
        remote = {**BLOIS_APT,
                  "address_label": "TEST Remote 45",
                  "lat": 47.7826, "lon": 2.7830,  # rural east Loiret
                  "code_commune": "45147", "commune": "Lorris", "postcode": "45260",
                  "surface": 55}
        r = s.post(f"{API}/properties", json=remote, timeout=60)
        # Either success (with widened radius notes) or 422 (no data)
        assert r.status_code in (201, 422)
        if r.status_code == 201:
            prop = r.json()
            est = prop["estimation"]
            widened_or_insufficient = est["insufficient_data"] or any(
                "élargi" in n or "insuffisant" in n.lower() for n in est["notes"]
            ) or est["confidence"]["radius_label"] not in ("À 500 m",)
            assert widened_or_insufficient, f"expected widening or insufficient flag, notes={est['notes']}, radius={est['confidence']['radius_label']}"
            TestProperties.created_ids.append(prop["id"])

    def test_validation_error_small_surface(self, s):
        bad = {**BLOIS_APT, "surface": 5}
        r = s.post(f"{API}/properties", json=bad, timeout=30)
        assert r.status_code == 422

    def test_list_properties_contains_created(self, s):
        r = s.get(f"{API}/properties", timeout=20)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()}
        for pid in TestProperties.created_ids:
            assert pid in ids

    def test_get_property(self, s):
        pid = TestProperties.created_ids[0]
        r = s.get(f"{API}/properties/{pid}", timeout=20)
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_get_unknown_property_404(self, s):
        r = s.get(f"{API}/properties/000000000000000000000000", timeout=20)
        assert r.status_code == 404

    def test_reestimate(self, s):
        pid = TestProperties.created_ids[0]
        r = s.post(f"{API}/properties/{pid}/reestimate", timeout=60)
        assert r.status_code == 200
        _check_estimation(r.json())

    def test_delete_and_soft_delete_semantics(self, s):
        pid = TestProperties.created_ids[0]
        r = s.delete(f"{API}/properties/{pid}", timeout=20)
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        # Not in list
        r2 = s.get(f"{API}/properties", timeout=20)
        ids = {p["id"] for p in r2.json()}
        assert pid not in ids
        # GET returns 404
        r3 = s.get(f"{API}/properties/{pid}", timeout=20)
        assert r3.status_code == 404
        TestProperties.created_ids.remove(pid)

    def test_delete_unknown_404(self, s):
        r = s.delete(f"{API}/properties/000000000000000000000000", timeout=20)
        assert r.status_code == 404

    @classmethod
    def teardown_class(cls):
        sess = requests.Session()
        for pid in cls.created_ids:
            try:
                sess.delete(f"{API}/properties/{pid}", timeout=15)
            except Exception:
                pass


# --- Validation endpoint ---
class TestValidation:
    def test_validation_report(self, s):
        r = s.get(f"{API}/validation", params={"n": 10}, timeout=120)
        assert r.status_code == 200
        b = r.json()
        assert b["n"] > 0
        for k in ("mape", "median_ape", "coverage", "by_confidence", "results"):
            assert k in b, f"missing {k}"
