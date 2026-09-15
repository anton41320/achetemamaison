"""Iteration 16 — Email/password auth, scoping, PDF ?t=, password flows, public routes."""
from __future__ import annotations

import os
import random
import string
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "delivered@resend.dev"
SEED_PASSWORD = "Estimo2026!"
SEED_PROPERTY_ID = "6aa02db9efd8f90925a5a758"


def _rand(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def seed_token(s):
    r = s.post(f"{API}/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def throwaway(s):
    email = f"qa-estimo-{_rand()}@gmail.com"
    password = "Motdepasse1"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    data = r.json()
    return {"email": email, "password": password, "token": data["access_token"], "user": data["user"]}


# ---------------- Auth registration/login ----------------

class TestAuthRegister:
    def test_duplicate_email_conflict(self, s):
        r = s.post(f"{API}/auth/register", json={"email": SEED_EMAIL, "password": "Whatever1234"})
        assert r.status_code == 409

    def test_short_password_422(self, s):
        r = s.post(f"{API}/auth/register", json={"email": f"qa-short-{_rand()}@gmail.com", "password": "short"})
        assert r.status_code == 422

    def test_invalid_email_422(self, s):
        r = s.post(f"{API}/auth/register", json={"email": "not-an-email", "password": "Motdepasse1"})
        assert r.status_code == 422

    def test_register_returns_token_and_user(self, throwaway):
        assert throwaway["token"]
        assert throwaway["user"]["email"] == throwaway["email"]


class TestAuthLogin:
    def test_login_wrong_password_401(self, s):
        r = s.post(f"{API}/auth/login", json={"email": SEED_EMAIL, "password": "wrong-password-xyz"})
        assert r.status_code == 401
        assert r.json().get("detail") == "Email ou mot de passe incorrect"

    def test_login_unknown_email_same_401(self, s):
        r = s.post(f"{API}/auth/login", json={"email": f"nobody-{_rand()}@gmail.com", "password": "Motdepasse1"})
        assert r.status_code == 401
        assert r.json().get("detail") == "Email ou mot de passe incorrect"

    def test_login_seed_ok(self, seed_token):
        assert seed_token


class TestAuthMe:
    def test_me_without_token_401(self, s):
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_tampered_token_401(self, s):
        r = s.get(f"{API}/auth/me", headers={"Authorization": "Bearer tampered.jwt.value"})
        assert r.status_code == 401

    def test_me_with_seed_token(self, s, seed_token):
        r = s.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {seed_token}"})
        assert r.status_code == 200
        assert r.json()["email"] == SEED_EMAIL


# ---------------- Scoping ----------------

class TestScoping:
    def test_properties_without_token_401(self, s):
        r = s.get(f"{API}/properties")
        assert r.status_code == 401

    def test_properties_seed_has_5(self, s, seed_token):
        r = s.get(f"{API}/properties", headers={"Authorization": f"Bearer {seed_token}"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 5, f"expected 5 seed properties, got {len(data)}"

    def test_throwaway_properties_empty(self, s, throwaway):
        r = s.get(f"{API}/properties", headers={"Authorization": f"Bearer {throwaway['token']}"})
        assert r.status_code == 200
        assert r.json() == []

    def test_throwaway_cannot_access_seed_property(self, s, throwaway):
        r = s.get(f"{API}/properties/{SEED_PROPERTY_ID}",
                  headers={"Authorization": f"Bearer {throwaway['token']}"})
        assert r.status_code == 404

    def test_throwaway_create_and_delete_property(self, s, throwaway, seed_token):
        h = {"Authorization": f"Bearer {throwaway['token']}"}
        g = s.get(f"{API}/geocode", params={"q": "Rue Denis Papin 41000 Blois"})
        assert g.status_code == 200, g.text
        results = g.json().get("results") or []
        assert results, f"geocode returned no results: {g.json()}"
        first = results[0]
        payload = {
            "address_label": first.get("label", "Rue Denis Papin 41000 Blois"),
            "lat": first["lat"],
            "lon": first["lon"],
            "code_commune": first["citycode"],
            "commune": first["city"],
            "postcode": first.get("postcode", "41000"),
            "property_type": "maison",
            "surface": 60,
            "rooms": 3,
            "bedrooms": 2,
            "condition": "correct",
        }
        r = s.post(f"{API}/properties", json=payload, headers=h)
        assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text}"
        created = r.json()
        pid = created.get("id") or created.get("_id")
        assert pid

        # Visible to throwaway
        r_own = s.get(f"{API}/properties", headers=h).json()
        assert any((p.get("id") or p.get("_id")) == pid for p in r_own)

        # Not visible to seed
        r_seed = s.get(f"{API}/properties", headers={"Authorization": f"Bearer {seed_token}"}).json()
        assert not any((p.get("id") or p.get("_id")) == pid for p in r_seed)

        d = s.delete(f"{API}/properties/{pid}", headers=h)
        assert d.status_code in (200, 204), d.text


# ---------------- PDF ?t= ----------------

class TestPDF:
    def test_pdf_without_token_401(self, s):
        r = s.get(f"{API}/properties/{SEED_PROPERTY_ID}/report.pdf")
        assert r.status_code == 401

    def test_pdf_with_header(self, s, seed_token):
        r = s.get(f"{API}/properties/{SEED_PROPERTY_ID}/report.pdf",
                  headers={"Authorization": f"Bearer {seed_token}"}, allow_redirects=False)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")

    def test_pdf_with_query_token(self, s, seed_token):
        r = s.get(f"{API}/properties/{SEED_PROPERTY_ID}/report.pdf", params={"t": seed_token},
                  allow_redirects=False)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")


# ---------------- Password flows ----------------

class TestForgotPassword:
    def test_forgot_known_email_generic(self, s):
        r = s.post(f"{API}/auth/forgot-password",
                   json={"email": SEED_EMAIL, "origin": "https://estimate-home.preview.emergentagent.com"})
        assert r.status_code == 200
        j = r.json()
        assert j.get("ok") is True
        assert "message" in j

    def test_forgot_unknown_email_same_generic(self, s):
        r = s.post(f"{API}/auth/forgot-password",
                   json={"email": f"unknown-{_rand()}@gmail.com",
                         "origin": "https://estimate-home.preview.emergentagent.com"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_forgot_invalid_origin_422(self, s):
        r = s.post(f"{API}/auth/forgot-password",
                   json={"email": SEED_EMAIL, "origin": "http://x"})
        assert r.status_code == 422


class TestResetPassword:
    def test_reset_with_bogus_code_400(self, s):
        r = s.post(f"{API}/auth/reset-password",
                   json={"token_or_code": "000000", "new_password": "Motdepasse2"})
        assert r.status_code == 400


class TestChangePasswordAndDelete:
    def test_change_password_flow_and_delete(self, s):
        # Register fresh throwaway to avoid coupling to session-scoped fixture
        email = f"qa-estimo-cp-{_rand()}@gmail.com"
        password = "Motdepasse1"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Wrong current password
        r = s.post(f"{API}/auth/change-password",
                   json={"current_password": "WrongPass1", "new_password": "Newpass1234"}, headers=h)
        assert r.status_code == 400

        # Correct change
        r = s.post(f"{API}/auth/change-password",
                   json={"current_password": password, "new_password": "Newpass1234"}, headers=h)
        assert r.status_code == 200

        # New password works
        r = s.post(f"{API}/auth/login", json={"email": email, "password": "Newpass1234"})
        assert r.status_code == 200
        token2 = r.json()["access_token"]
        h2 = {"Authorization": f"Bearer {token2}"}

        # Delete with wrong password
        r = s.delete(f"{API}/auth/account", json={"password": "WrongPass1"}, headers=h2)
        assert r.status_code == 400

        # Delete with correct password
        r = s.delete(f"{API}/auth/account", json={"password": "Newpass1234"}, headers=h2)
        assert r.status_code == 200

        # /me now 401
        r = s.get(f"{API}/auth/me", headers=h2)
        assert r.status_code == 401


# ---------------- Public routes still open ----------------

class TestPublicRoutes:
    def test_health(self, s):
        r = s.get(f"{API}/health")
        assert r.status_code == 200

    def test_geocode(self, s):
        r = s.get(f"{API}/geocode", params={"q": "Blois"})
        assert r.status_code == 200

    def test_dvf_status(self, s):
        r = s.get(f"{API}/dvf/status")
        assert r.status_code == 200

    def test_models_hedonic(self, s):
        r = s.get(f"{API}/models/hedonic")
        assert r.status_code == 200

    def test_estimate_preview(self, s):
        # Build valid preview payload using geocode
        g = s.get(f"{API}/geocode", params={"q": "Rue Denis Papin 41000 Blois"}).json()
        first = (g.get("results") or [{}])[0]
        payload = {
            "address_label": first.get("label", "Rue Denis Papin 41000 Blois"),
            "lat": first["lat"],
            "lon": first["lon"],
            "code_commune": first["citycode"],
            "commune": first["city"],
            "postcode": first.get("postcode", "41000"),
            "property_type": "maison",
            "surface": 90,
            "rooms": 4,
            "bedrooms": 3,
            "condition": "correct",
        }
        r = s.post(f"{API}/estimate/preview", json=payload)
        assert r.status_code == 200, r.text


# ---------------- Cleanup: delete session throwaway ----------------

def test_zz_cleanup_throwaway(s, throwaway):
    r = s.delete(f"{API}/auth/account", json={"password": throwaway["password"]},
                 headers={"Authorization": f"Bearer {throwaway['token']}"})
    assert r.status_code == 200
