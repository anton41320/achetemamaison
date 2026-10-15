"""Tests pour les pages publiques (phases 2-4) : prix immobilier, sitemap, robots."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://estimate-home.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    return s


# ---------- /api/public/prices (départements) ----------
class TestPublicPricesDepartements:
    def test_prices_list_all_97(self, api):
        r = api.get(f"{BASE_URL}/api/public/prices", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "departements" in data
        depts = data["departements"]
        # 95 métropolitains (dont 2A, 2B, sans 20) + 971/972/973/974 = ~97
        assert len(depts) >= 95, f"Expected >= 95 departements, got {len(depts)}"
        # Structure
        for d in depts[:5]:
            assert "code" in d and "name" in d
            assert "maison" in d and "appartement" in d
        # Loir-et-Cher (41) présent
        codes = {d["code"] for d in depts}
        assert "41" in codes
        assert "2A" in codes and "2B" in codes


# ---------- /api/public/prices/41 (commune list) ----------
class TestPublicPricesDept:
    def test_dept_41_contains_blois_first_sorted_by_count(self, api):
        r = api.get(f"{BASE_URL}/api/public/prices/41", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == "41"
        assert "Loir-et-Cher" in data["name"]
        communes = data["communes"]
        assert len(communes) > 10
        # Trié par count décroissant
        counts = [c["count"] for c in communes]
        assert counts == sorted(counts, reverse=True), "communes should be sorted by count desc"
        # Blois en tête (chef-lieu, plus grosse ville 41)
        assert "Blois" in communes[0]["name"], f"Expected Blois first, got {communes[0]['name']}"

    def test_dept_99_not_found(self, api):
        r = api.get(f"{BASE_URL}/api/public/prices/99", timeout=15)
        assert r.status_code == 404


# ---------- /api/public/prices/41/41061 (Cormeray) ----------
class TestPublicPricesCommune:
    def test_cormeray_structure(self, api):
        r = api.get(f"{BASE_URL}/api/public/prices/41/41061", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["insee"] == "41061"
        assert data["dept"] == "41"
        assert "Cormeray" in data["name"]
        # maison.median_pm2 numérique non nul
        assert data["maison"] is not None, "Cormeray should have maison data"
        assert isinstance(data["maison"]["median_pm2"], (int, float))
        assert data["maison"]["median_pm2"] > 0
        assert isinstance(data["maison"]["count"], int) and data["maison"]["count"] > 0
        # trend présent (liste)
        assert "trend" in data and isinstance(data["trend"], list)
        # recent_sales <= 12
        assert "recent_sales" in data
        assert isinstance(data["recent_sales"], list)
        assert len(data["recent_sales"]) <= 12
        # neighbours
        assert "neighbours" in data and isinstance(data["neighbours"], list)


# ---------- /api/public/sitemap.xml ----------
class TestSitemap:
    def test_sitemap_xml_content_and_size(self, api):
        r = api.get(f"{BASE_URL}/api/public/sitemap.xml", timeout=30)
        assert r.status_code == 200
        assert "xml" in r.headers.get("content-type", "").lower()
        body = r.text
        assert body.startswith("<?xml")
        locs = re.findall(r"<loc>", body)
        assert len(locs) > 10000, f"Expected > 10000 <loc>, got {len(locs)}"


# ---------- /robots.txt ----------
class TestRobots:
    def test_robots_served_by_frontend(self, api):
        r = api.get(f"{BASE_URL}/robots.txt", timeout=15)
        assert r.status_code == 200
        body = r.text
        assert "Sitemap:" in body
        assert "/api/public/sitemap.xml" in body
