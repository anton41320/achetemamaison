"""Phase 6 — Dossier de vente: checklist, document upload+OCR, validation, overrides."""
from __future__ import annotations

import io
import os
import time
from datetime import date

import pytest
import requests
from PIL import Image, ImageDraw, ImageFont

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
DEMO_PROPERTY_ID = "6aa02db9efd8f90925a5a758"  # maison built 1990 (per iteration spec)


def _text_jpeg(lines: list[str], size=(900, 1200)) -> bytes:
    img = Image.new("RGB", size, (245, 245, 240))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    y = 60
    for line in lines:
        d.text((60, y), line, fill=(20, 20, 20), font=font)
        y += 60
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92)
    return out.getvalue()


# ---------------- Checklist: maison built 1990 ----------------
class TestDossierMaison:
    def test_dossier_maison_shape_and_required_items(self):
        r = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}/dossier", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["property_id"] == DEMO_PROPERTY_ID
        assert "items" in d and isinstance(d["items"], list)
        assert "progress" in d
        progress = d["progress"]
        assert set(progress.keys()) >= {"done", "total_required", "pct"}

        by_key = {it["key"]: it for it in d["items"]}
        # Maison built 1990 → required
        for k in ("titre_propriete", "dpe", "erp", "amiante"):
            assert k in by_key, f"missing item {k}"
            assert by_key[k]["required"] is True, f"{k} should be required"
        # These must be present (not necessarily required=True)
        for k in ("electricite", "gaz", "termites", "assainissement", "geotechnique", "taxe_fonciere"):
            assert k in by_key, f"missing item {k}"
        # NOT for maison
        for k in ("carrez", "pv_ag", "reglement_copro", "pre_etat_date"):
            assert k not in by_key, f"{k} should NOT be present for maison"

        # Each item has documents list + status
        for it in d["items"]:
            assert "status" in it
            assert "documents" in it and isinstance(it["documents"], list)


# ---------------- Checklist: appartement built 1975 ----------------
@pytest.fixture(scope="module")
def apt_property_id():
    payload = {
        "address_label": "TEST Blois appartement",
        "lat": 47.586414, "lon": 1.335664,
        "code_commune": "41018", "commune": "Blois", "postcode": "41000",
        "property_type": "appartement",
        "surface": 65, "rooms": 3, "bedrooms": 2, "year_built": 1975,
        "condition": "correct",
    }
    r = requests.post(f"{API}/properties", json=payload, timeout=60)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{API}/properties/{pid}", timeout=15)


class TestDossierAppartement:
    def test_appartement_has_copro_items_required(self, apt_property_id):
        r = requests.get(f"{API}/properties/{apt_property_id}/dossier", timeout=15)
        assert r.status_code == 200, r.text
        by_key = {it["key"]: it for it in r.json()["items"]}
        for k in ("carrez", "reglement_copro", "pv_ag", "pre_etat_date"):
            assert k in by_key, f"missing copro item {k}"
            assert by_key[k]["required"] is True, f"{k} must be required for appartement"


# ---------------- Upload + OCR (max 1 LLM call for credit) ----------------
class TestDocumentUpload:
    def test_invalid_item_key_returns_422(self):
        files = {"file": ("x.jpg", _text_jpeg(["test"]), "image/jpeg")}
        r = requests.post(
            f"{API}/properties/{DEMO_PROPERTY_ID}/documents",
            files=files, data={"item_key": "nonexistent_key"}, timeout=30,
        )
        assert r.status_code == 422, r.text

    def test_unknown_property_returns_404(self):
        files = {"file": ("x.jpg", _text_jpeg(["test"]), "image/jpeg")}
        r = requests.post(
            f"{API}/properties/6aa02db9efd8f90925a5a999/documents",
            files=files, data={"item_key": "taxe_fonciere"}, timeout=30,
        )
        assert r.status_code == 404, r.text

    def test_upload_taxe_fonciere_triggers_ocr(self):
        """Single LLM call — the core happy path. Cleanup after."""
        img = _text_jpeg([
            "AVIS DE TAXE FONCIERE",
            "Annee 2025",
            "Reference AVT-2025-000123",
            "Montant total: 1 250 EUR",
            "Commune: Blois (41)",
            "Date d'emission: 01/09/2025",
        ])
        files = {"file": ("TEST_taxe_fonciere.jpg", img, "image/jpeg")}
        t0 = time.time()
        r = requests.post(
            f"{API}/properties/{DEMO_PROPERTY_ID}/documents",
            files=files, data={"item_key": "taxe_fonciere"}, timeout=60,
        )
        elapsed = time.time() - t0
        assert r.status_code == 201, f"upload failed ({elapsed:.1f}s): {r.text}"
        d = r.json()
        did = d["id"]
        try:
            assert d["item_key"] == "taxe_fonciere"
            assert d["file_path"].startswith("estimo/documents/")
            assert d["ocr_status"] == "done", f"ocr_status={d['ocr_status']} ocr_error={d.get('ocr_error')}"
            assert d["ocr"] is not None
            assert d["ocr"].get("document_type")
            assert d["ocr"].get("title")
            assert d["status"] == "a_verifier"

            # GET document
            g = requests.get(f"{API}/documents/{did}", timeout=15)
            assert g.status_code == 200

            # File served
            f = requests.get(f"{API}/files/{d['file_path']}", timeout=30)
            assert f.status_code == 200
            assert f.headers["Content-Type"].startswith("image/jpeg")

            # Validate → status valide, propagates to dossier item
            body = {
                "fields": {
                    "document_type": "taxe_fonciere",
                    "title": "Taxe foncière 2025",
                    "issuer": "DGFiP",
                    "document_date": "2025-09-01",
                    "validity_date": None,
                    "address_found": None,
                    "key_fields": [{"label": "Montant", "value": "1250 €"}],
                    "warnings": [],
                    "summary": "Avis taxe foncière 2025.",
                    "confidence": 0.9,
                },
                "validated": True,
            }
            v = requests.put(f"{API}/documents/{did}/validate", json=body, timeout=15)
            assert v.status_code == 200, v.text
            vd = v.json()
            assert vd["validated"] is True
            assert vd["status"] == "valide"

            # Dossier reflects it
            doss = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}/dossier", timeout=15).json()
            tf = next(it for it in doss["items"] if it["key"] == "taxe_fonciere")
            assert tf["status"] == "valide"

            # DELETE + subsequent GET 404, file endpoint 404
            dr = requests.delete(f"{API}/documents/{did}", timeout=15)
            assert dr.status_code == 200
            g2 = requests.get(f"{API}/documents/{did}", timeout=15)
            assert g2.status_code == 404
            did = None  # cleaned
        finally:
            if did:
                requests.delete(f"{API}/documents/{did}", timeout=15)


# ---------------- DPE validation (expiry from document_date + 10 years) ----------------
class TestDpeExpiry:
    def test_validate_dpe_computes_expiry_10_years(self):
        """Use existing demo DPE document if present (do not delete it)."""
        doss = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}/dossier", timeout=15).json()
        dpe_item = next((it for it in doss["items"] if it["key"] == "dpe"), None)
        assert dpe_item is not None
        if not dpe_item["documents"]:
            pytest.skip("No demo DPE document present to validate")
        did = dpe_item["documents"][0]["id"]
        body = {
            "fields": {
                "document_type": "dpe",
                "title": "DPE",
                "issuer": "Diagnostiqueur X",
                "document_date": "2024-03-12",
                "validity_date": None,
                "address_found": None,
                "key_fields": [{"label": "Classe", "value": "D"}],
                "warnings": [],
                "summary": "DPE valide.",
                "confidence": 0.9,
            },
            "validated": True,
        }
        r = requests.put(f"{API}/documents/{did}/validate", json=body, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["validated"] is True
        exp = d.get("expiry_date")
        assert exp, "expiry_date should be computed"
        # ~10 years from 2024-03-12
        assert exp.startswith("2034-03"), f"expected 2034-03 prefix, got {exp}"


# ---------------- Checklist override ----------------
class TestChecklistOverride:
    def test_override_gaz_non_applicable_and_restore(self):
        r = requests.put(
            f"{API}/properties/{DEMO_PROPERTY_ID}/dossier/gaz",
            json={"status_override": "non_applicable"}, timeout=15,
        )
        assert r.status_code == 200, r.text
        gaz = next(it for it in r.json()["items"] if it["key"] == "gaz")
        assert gaz["status"] == "non_applicable"

        r2 = requests.put(
            f"{API}/properties/{DEMO_PROPERTY_ID}/dossier/gaz",
            json={"status_override": None}, timeout=15,
        )
        assert r2.status_code == 200
        gaz2 = next(it for it in r2.json()["items"] if it["key"] == "gaz")
        assert gaz2["status"] != "non_applicable"

    def test_override_unknown_item_returns_404(self):
        r = requests.put(
            f"{API}/properties/{DEMO_PROPERTY_ID}/dossier/does_not_exist",
            json={"status_override": None}, timeout=15,
        )
        assert r.status_code == 404


# ---------------- Regression ----------------
class TestRegression:
    def test_property_detail_still_ok(self):
        r = requests.get(f"{API}/properties/{DEMO_PROPERTY_ID}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("estimation") is not None
        assert d["estimation"].get("low") is not None
