"""Deployment-fix regression tests.
Covers: top-level /health probe, /api/health, dvf status, models, properties, next-steps, alerts,
and jobs.start (multiprocessing spawn) semantics from /app/backend/jobs.py.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL"
) else "https://estimate-home.preview.emergentagent.com"
LOCAL_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def s() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"Accept": "application/json"})
    return sess


# ---------------------------------------------------------------- health probes
class TestHealth:
    def test_local_root_health_json(self, s):
        """Backend must expose GET /health (no /api prefix) — this is what platform probes hit."""
        r = s.get(f"{LOCAL_URL}/health", timeout=5)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("status") == "ok"

    def test_public_root_health_may_be_html(self, s):
        """Preview ingress routes non-/api paths to the frontend (Expo web).
        Deployment ingress will route /health to the backend and get JSON.
        We only require HTTP 200 here."""
        r = s.get(f"{BASE_URL}/health", timeout=10)
        assert r.status_code == 200

    def test_public_api_health(self, s):
        r = s.get(f"{BASE_URL}/api/health", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert isinstance(body["departments"], list) and body["departments"]


# ------------------------------------------------------------ DVF & models
class TestDvfModels:
    def test_dvf_status_idle_with_data(self, s):
        r = s.get(f"{BASE_URL}/api/dvf/status", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["state"] == "idle", d
        assert d["total"] > 100_000, d["total"]
        assert len(d["departments"]) >= 1

    def test_hedonic_available_not_training(self, s):
        d = s.get(f"{BASE_URL}/api/models/hedonic", timeout=15).json()
        assert d.get("available") is True
        assert d.get("training") is False

    def test_ml_model_available(self, s):
        r = s.get(f"{BASE_URL}/api/models/ml", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("available") is True
        assert d.get("training") is False


# ------------------------------------------------------------ home-screen queries
class TestHomeQueries:
    def test_properties_list_ok(self, s):
        r = s.get(f"{BASE_URL}/api/properties", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for p in items:
            assert p.get("estimation"), f"missing estimation on {p.get('id')}"
            assert "value" in p["estimation"]

    def test_next_steps_ok(self, s):
        r = s.get(f"{BASE_URL}/api/next-steps", timeout=15)
        assert r.status_code == 200
        assert "properties" in r.json()

    def test_alerts_ok(self, s):
        r = s.get(f"{BASE_URL}/api/alerts", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "alerts" in d and "as_of" in d


# ------------------------------------------------------------ referenced regressions
class TestRegressions:
    PID = "6aa02db9efd8f90925a5a758"

    def test_referenced_property_has_estimation(self, s):
        r = s.get(f"{BASE_URL}/api/properties/{self.PID}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("estimation")
        assert isinstance(d["estimation"].get("value"), (int, float))


# ------------------------------------------------------------ jobs.start (spawn subprocess)
class TestJobsModule:
    def test_start_uses_spawn_and_is_running_flag(self):
        """train_models(False, False) is a no-op subprocess: should start, report running, then exit."""
        import sys
        sys.path.insert(0, str(ROOT))
        import jobs
        assert jobs.is_running() is False, "no job should be running at test start"
        started = jobs.start(
            jobs.train_models, os.environ["MONGO_URL"], os.environ["DB_NAME"], False, False
        )
        assert started is True
        # a second start while running must be rejected
        second = jobs.start(
            jobs.train_models, os.environ["MONGO_URL"], os.environ["DB_NAME"], False, False
        )
        assert second is False
        # wait for the child to finish
        for _ in range(30):
            if not jobs.is_running():
                break
            time.sleep(0.5)
        assert jobs.is_running() is False
