"""Iter 22 backend regression:
- Confidence badge/score removed from report PDFs
- Dossier endpoint is fast (uses cache with background refresh)
- Non-regression on properties + estimation
"""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else "https://estimate-home.preview.emergentagent.com"
EMAIL = "delivered@resend.dev"
PASSWORD = "Estimo2026!"
PROP_A = "6aa3f68d440f04920cdaffde"
PROP_B = "6aa02db9efd8f90925a5a758"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ------- Dossier fast endpoint -------
@pytest.mark.parametrize("pid", [PROP_A, PROP_B])
def test_dossier_fast_and_shape(headers, pid):
    """Dossier must be < 2s on all 3 consecutive calls and expose items[], progress{}, locked (bool)."""
    times = []
    last = None
    for _ in range(3):
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/properties/{pid}/dossier", headers=headers, timeout=10)
        times.append(time.time() - t0)
        assert r.status_code == 200, r.text
        last = r.json()
    print(f"[{pid}] dossier times: {times}")
    # Every call must be < 2s
    for i, dt in enumerate(times):
        assert dt < 2.0, f"Call #{i+1} for {pid} took {dt:.2f}s (>2s)"
    # Payload shape
    assert isinstance(last.get("items"), list), f"missing items: {list(last.keys())}"
    assert isinstance(last.get("progress"), dict), f"missing progress: {list(last.keys())}"
    assert isinstance(last.get("locked"), bool), f"missing locked bool: {list(last.keys())}"


# ------- Report PDF must not contain confidence wording -------
def _pdf_text(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    txt = []
    for p in reader.pages:
        try:
            txt.append(p.extract_text() or "")
        except Exception:
            pass
    return "\n".join(txt)


def test_report_pdf_no_confidence(headers):
    r = requests.get(f"{BASE_URL}/api/properties/{PROP_A}/report.pdf", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
    text = _pdf_text(r.content)
    low = text.lower()
    assert "confiance" not in low, "PDF still contains 'confiance'"
    assert "niveau de confiance" not in low
    # Positive markers
    assert ("périmètre" in low or "perimetre" in low or "ventes comparables" in low), \
        "PDF missing expected analysis markers"


def test_notaire_pdf_no_confidence(headers):
    r = requests.get(f"{BASE_URL}/api/properties/{PROP_B}/notaire.pdf", headers=headers, timeout=30)
    # 402 acceptable if account not entitled
    assert r.status_code in (200, 402, 403), r.text
    if r.status_code == 200:
        assert r.headers.get("content-type", "").startswith("application/pdf")
        text = _pdf_text(r.content).lower()
        assert "confiance" not in text, "notaire.pdf still contains 'confiance'"


# ------- Non-regression on estimation -------
def test_list_properties(headers):
    r = requests.get(f"{BASE_URL}/api/properties", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_property_detail_estimation(headers):
    r = requests.get(f"{BASE_URL}/api/properties/{PROP_A}", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    est = body.get("estimation")
    assert est, f"missing estimation: {list(body.keys())}"
    for k in ("value", "low", "high"):
        assert k in est, f"missing estimation.{k}"
    assert isinstance(est["value"], (int, float)) and est["value"] > 0
