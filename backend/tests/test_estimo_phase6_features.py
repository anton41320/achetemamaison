"""Phase 6 tests: declared equipment features applied as transparent adjustments."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
EXISTING_PID = "6aa02db9efd8f90925a5a758"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def _find(adjs, key):
    return next((a for a in adjs if a["key"] == key), None)


class TestPutFeaturesOnExisting:
    """PUT /api/properties/{id} with declared features on an existing property."""

    def test_put_with_features_creates_adjustments(self, s):
        body = {
            "features": {"pool": "enterree", "single_storey": True, "heating": "fioul", "dpe": "F", "garage": "un"},
        }
        r = s.put(f"{API}/properties/{EXISTING_PID}", json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        adjs = data["estimation"]["adjustments"]
        # Check individual adjustments
        pool = _find(adjs, "feat_pool")
        ss = _find(adjs, "feat_single_storey")
        heat = _find(adjs, "feat_heating")
        dpe = _find(adjs, "feat_dpe")
        garage = _find(adjs, "feat_garage")
        assert pool is not None and pool["pct"] > 0
        assert ss is not None and ss["pct"] > 0
        assert heat is not None and heat["pct"] < 0
        assert dpe is not None and dpe["pct"] < 0
        assert garage is not None and garage["pct"] > 0
        # Base % expected (before scaling): 0.06+0.03-0.04-0.09+0.03 = -0.01 (no scaling)
        assert pool["pct"] == pytest.approx(0.06, abs=0.005)
        assert ss["pct"] == pytest.approx(0.03, abs=0.005)
        assert heat["pct"] == pytest.approx(-0.04, abs=0.005)
        assert dpe["pct"] == pytest.approx(-0.09, abs=0.005)
        assert garage["pct"] == pytest.approx(0.03, abs=0.005)
        # Features persisted
        f = data["features"]
        assert f["pool"] == "enterree"
        assert f["single_storey"] is True
        assert f["heating"] == "fioul"
        assert f["dpe"] == "F"
        assert f["garage"] == "un"
        # Hedonic factors contain 'features'
        hed = data["estimation"].get("hedonic")
        if hed:  # hedonic may be missing if model not trained
            keys = [f["key"] for f in hed["factors"]]
            assert "features" in keys, f"hedonic factors keys: {keys}"

    def test_put_clears_features(self, s):
        body = {
            "surface": 120,
            "features": {
                "pool": None, "fenced": None, "motorized_gate": None, "terrace": None,
                "garage": None, "outbuilding": None, "orientation": None, "single_storey": None,
                "basement": None, "convertible_attic": None, "bathrooms": None, "heating": None,
                "dpe": None, "double_glazing": None, "air_conditioning": None, "solar_panels": None,
            },
        }
        r = s.put(f"{API}/properties/{EXISTING_PID}", json=body)
        assert r.status_code == 200, r.text
        adjs = r.json()["estimation"]["adjustments"]
        feat_adjs = [a for a in adjs if a["key"].startswith("feat_")]
        assert feat_adjs == [], f"unexpected feature adjustments: {feat_adjs}"

    def test_put_invalid_surface(self, s):
        r = s.put(f"{API}/properties/{EXISTING_PID}", json={"surface": 5})
        assert r.status_code == 422

    def test_put_unknown_id(self, s):
        r = s.put(f"{API}/properties/000000000000000000000000", json={"surface": 100})
        assert r.status_code == 404


class TestCreateAppartementWithFeatures:
    """POST /api/properties for an apartment with features."""

    created_id = None

    def test_create_appartement_with_features(self, s):
        body = {
            "address_label": "TEST_Blois Appartement",
            "lat": 47.586414, "lon": 1.335664,
            "code_commune": "41018", "commune": "Blois", "postcode": "41000",
            "property_type": "appartement",
            "surface": 65, "rooms": 3, "bedrooms": 2,
            "condition": "correct",
            "features": {"floor": 4, "elevator": False, "balcony": True, "parking": True, "fenced": True},
        }
        r = s.post(f"{API}/properties", json=body)
        assert r.status_code == 201, r.text
        data = r.json()
        TestCreateAppartementWithFeatures.created_id = data["id"]

        adjs = data["estimation"]["adjustments"]
        floor = _find(adjs, "feat_floor")
        balcony = _find(adjs, "feat_balcony")
        parking = _find(adjs, "feat_parking")
        fenced = _find(adjs, "feat_fenced")
        assert floor is not None and floor["pct"] == pytest.approx(-0.04, abs=0.005)
        assert balcony is not None and balcony["pct"] == pytest.approx(0.03, abs=0.005)
        assert parking is not None and parking["pct"] == pytest.approx(0.04, abs=0.005)
        # maison-only feature must be ignored for apartment
        assert fenced is None, "fenced adjustment must not be applied to appartement"

    def test_cleanup_created(self, s):
        pid = TestCreateAppartementWithFeatures.created_id
        if not pid:
            pytest.skip("no created property")
        r = s.delete(f"{API}/properties/{pid}")
        assert r.status_code == 200


class TestReportPdf:
    def test_report_pdf_still_ok(self, s):
        r = s.get(f"{API}/properties/{EXISTING_PID}/report.pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1000
