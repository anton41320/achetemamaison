"""Phase 9 tests: hedonic v2 (micro_location) + next-steps + quick regressions."""
import os
import pytest
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

SOINGS_PID = "6aa02db9efd8f90925a5a758"
BLOIS_PIDS = ["6aa02db9efd8f90925a5a756", "6aa02c492f09d3116cfaf507", "6aa02c392f09d3116cfaf505"]


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---- Hedonic v2 model endpoint ----
class TestHedonicModel:
    def test_model_endpoint(self, s):
        r = s.get(f"{API}/models/hedonic", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("available") is True, d
        assert d.get("name") == "hedonic_v2", d.get("name")
        coefs = d.get("coefficients") or {}
        assert "log_surface_maison" in coefs
        assert "rooms_maison" in coefs
        holdout_local = d.get("holdout_local")
        assert holdout_local is not None, "holdout_local missing"
        assert "median_ape" in holdout_local
        assert "r2_log" in holdout_local
        assert "without_local" in holdout_local
        assert isinstance(holdout_local["without_local"], dict)


# ---- Estimate preview with hedonic v2 ----
class TestEstimatePreview:
    def test_villefranche_preview(self, s):
        payload = {
            "address_label": "Villefranche",
            "lat": 47.30566,
            "lon": 1.763254,
            "code_commune": "41280",
            "commune": "Villefranche-sur-Cher",
            "postcode": "41200",
            "property_type": "maison",
            "surface": 140,
            "rooms": 6,
            "bedrooms": 4,
            "condition": "correct",
            "land_surface": 800,
        }
        r = s.post(f"{API}/estimate/preview", json=payload, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        est = d.get("estimation") or d
        # Method version
        assert est.get("method") == "comparables_dvf_v3", est.get("method")
        hed = d.get("hedonic") or est.get("hedonic")
        assert hed is not None, "hedonic missing"
        assert hed.get("model_version") == "hedonic_v2", hed.get("model_version")
        factor_keys = {f["key"] for f in hed.get("factors", [])}
        for k in ("location", "surface", "rooms", "land", "micro_location"):
            assert k in factor_keys, f"missing factor {k}: got {factor_keys}"
        agreement = hed.get("agreement")
        assert agreement in ("convergent", "ecart_modere"), f"agreement={agreement}, delta={hed.get('delta_vs_comparables_pct')}"
        delta = abs(hed.get("delta_vs_comparables_pct") or 0.0)
        assert delta < 0.25, delta
        # half-width <= 15%
        value = hed["value"]
        low = hed["low"]
        high = hed["high"]
        hw = (high - low) / (2 * value)
        assert hw <= 0.15 + 0.001, f"hedonic hw={hw:.4f}"


# ---- GET property auto-refresh ----
class TestPropertyGet:
    def test_soings_property(self, s):
        r = s.get(f"{API}/properties/{SOINGS_PID}", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        est = d.get("estimation") or {}
        assert est.get("method") == "comparables_dvf_v3", est.get("method")
        hed = d.get("hedonic") or est.get("hedonic")
        assert hed is not None, "hedonic missing on property"
        factor_keys = {f["key"] for f in hed.get("factors", [])}
        assert "micro_location" in factor_keys, factor_keys
        assert hed.get("agreement") == "convergent", (hed.get("agreement"), hed.get("delta_vs_comparables_pct"))


# ---- Next steps ----
class TestNextSteps:
    def test_list_next_steps(self, s):
        r = s.get(f"{API}/next-steps", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        props = d.get("properties")
        assert isinstance(props, list) and props, d
        soings = next((p for p in props if p["property_id"] == SOINGS_PID), None)
        assert soings is not None, [p["property_id"] for p in props]
        assert len(soings["steps"]) == 6
        for st in soings["steps"]:
            assert st["key"] in ("features", "target", "dossier", "photos", "listing", "export")
            assert "label" in st and "done" in st and "route" in st and "detail" in st
        assert soings["total"] == 5, soings["total"]
        assert soings["done"] == 4, soings["done"]
        assert soings["next"]["key"] == "dossier", soings["next"]
        assert soings["next"]["label"].startswith("Ajouter :"), soings["next"]["label"]
        assert soings["next"]["route"] == f"/property/{SOINGS_PID}/dossier"

    def test_blois_next_features(self, s):
        r = s.get(f"{API}/next-steps", timeout=60)
        assert r.status_code == 200
        d = r.json()
        blois = None
        for p in d["properties"]:
            if p["property_id"] in BLOIS_PIDS and p["next"] and p["next"]["key"] == "features":
                blois = p
                break
        assert blois is not None, [(p["property_id"], p["next"] and p["next"]["key"]) for p in d["properties"]]
        assert blois["next"]["route"] == f"/property/{blois['property_id']}/edit"

    def test_property_next_steps_route(self, s):
        r = s.get(f"{API}/properties/{SOINGS_PID}/next-steps", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["property_id"] == SOINGS_PID
        assert d["total"] == 5
        assert d["next"]["key"] == "dossier"

    def test_property_next_steps_404(self, s):
        r = s.get(f"{API}/properties/6aa02db9efd8f909deadbeef/next-steps", timeout=30)
        assert r.status_code == 404, r.status_code


# ---- Regressions ----
class TestRegression:
    def test_report_pdf(self, s):
        r = s.get(f"{API}/properties/{SOINGS_PID}/report.pdf", timeout=60)
        assert r.status_code == 200, r.status_code
        assert r.headers.get("content-type", "").startswith("application/pdf")

    def test_final(self, s):
        r = s.get(f"{API}/properties/{SOINGS_PID}/final", timeout=30)
        assert r.status_code == 200, r.status_code

    def test_target(self, s):
        r = s.get(f"{API}/properties/{SOINGS_PID}/target", timeout=30)
        assert r.status_code == 200, r.status_code

    def test_alerts(self, s):
        r = s.get(f"{API}/alerts", timeout=30)
        assert r.status_code == 200, r.status_code
