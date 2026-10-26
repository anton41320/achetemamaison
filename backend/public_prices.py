"""Pages publiques « Prix immobilier » (SEO) : médianes DVF par département et par commune, plan du site.

Données : ventes DVF déjà ingérées (collection `dvf_sales`, France entière). Agrégations Mongo (`$median`, MongoDB ≥ 7) mises en
cache mémoire 24 h : les pages publiques ne doivent jamais peser sur l'API métier. Aucune donnée personnelle : DVF est une base
publique (prix, surface, date, commune) et les ventes affichées sont agrégées ou limitées aux caractéristiques du bien.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from departements import ALL_FRANCE

router = APIRouter(prefix="/api/public", tags=["public"])
db = None  # injecté par server.py

DEPT_NAMES = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche",
    "08": "Ardennes", "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal",
    "16": "Charente", "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud", "2B": "Haute-Corse", "21": "Côte-d'Or",
    "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire",
    "38": "Isère", "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique", "45": "Loiret",
    "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne", "52": "Haute-Marne", "53": "Mayenne",
    "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise", "61": "Orne",
    "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques", "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin",
    "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris",
    "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne",
    "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis", "94": "Val-de-Marne", "95": "Val-d'Oise", "971": "Guadeloupe",
    "972": "Martinique", "973": "Guyane", "974": "La Réunion",
}
MIN_SALES_COMMUNE = 5  # en dessous, la médiane n'est pas significative : commune listée sans prix
MIN_SALES_SITEMAP = 10
TTL = 24 * 3600

_cache: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}


async def cached(key: str, fn: Callable[[], Awaitable[Any]]) -> Any:
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
        value = await fn()
        _cache[key] = (time.time() + TTL, value)
        return value


def _years() -> tuple[int, int]:
    """Fenêtre glissante : 3 derniers millésimes (DVF est publié avec ~6 mois de décalage)."""
    y = datetime.now(timezone.utc).year
    return y - 2, y


def _median_group(by: dict) -> list[dict]:
    return [{"$group": {"_id": by, "median_pm2": {"$median": {"input": "$price_m2", "method": "approximate"}},
                        "median_price": {"$median": {"input": "$price", "method": "approximate"}},
                        "median_surface": {"$median": {"input": "$surface", "method": "approximate"}},
                        "count": {"$sum": 1}, "commune": {"$first": "$commune"}, "code_postal": {"$first": "$code_postal"}}}]


def _fmt(doc: dict | None) -> dict | None:
    if not doc or doc["count"] < MIN_SALES_COMMUNE:
        return None
    return {"median_pm2": round(doc["median_pm2"]), "median_price": round(doc["median_price"], -3), "median_surface": round(doc["median_surface"]), "count": doc["count"]}


def _slug(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return "".join(c if c.isalnum() else "-" for c in s).strip("-").replace("--", "-")


@router.get("/prices")
async def prices_departements():
    """Médianes €/m² par département (maison / appartement), 3 derniers millésimes."""
    y0, y1 = _years()

    async def build():
        rows = await db.dvf_sales.aggregate([{"$match": {"year": {"$gte": y0, "$lte": y1}}}, *_median_group({"dept": "$dept", "type": "$type"})],
                                            allowDiskUse=True).to_list(1000)
        out: dict[str, dict] = {}
        for r in rows:
            d = out.setdefault(r["_id"]["dept"], {"code": r["_id"]["dept"], "name": DEPT_NAMES.get(r["_id"]["dept"], r["_id"]["dept"]), "maison": None, "appartement": None, "count": 0})
            d[r["_id"]["type"]] = _fmt(r)
            d["count"] += r["count"]
        for code in ALL_FRANCE:
            out.setdefault(code, {"code": code, "name": DEPT_NAMES.get(code, code), "maison": None, "appartement": None, "count": 0})
        return {"years": [y0, y1], "departements": sorted(out.values(), key=lambda d: (len(d["code"]), d["code"]))}

    return await cached("depts", build)


@router.get("/prices/{dept}")
async def prices_dept(dept: str):
    dept = dept.upper()
    if dept not in DEPT_NAMES:
        raise HTTPException(status_code=404, detail="Département inconnu")
    y0, y1 = _years()

    async def build():
        rows = await db.dvf_sales.aggregate([{"$match": {"dept": dept, "year": {"$gte": y0, "$lte": y1}}},
                                             *_median_group({"insee": "$code_commune", "type": "$type"})], allowDiskUse=True).to_list(5000)
        communes: dict[str, dict] = {}
        for r in rows:
            c = communes.setdefault(r["_id"]["insee"], {"insee": r["_id"]["insee"], "name": r["commune"], "slug": _slug(r["commune"]), "code_postal": r["code_postal"],
                                                       "maison": None, "appartement": None, "count": 0})
            c[r["_id"]["type"]] = _fmt(r)
            c["count"] += r["count"]
        pops = {p["_id"]: p.get("population") for p in await db.communes.find({"dept": dept}, {"population": 1}).to_list(2000)}
        for c in communes.values():
            c["population"] = pops.get(c["insee"])
        all_rows = await db.dvf_sales.aggregate([{"$match": {"dept": dept, "year": {"$gte": y0, "$lte": y1}}}, *_median_group({"type": "$type"})]).to_list(10)
        summary = {r["_id"]["type"]: _fmt(r) for r in all_rows}
        return {"code": dept, "name": DEPT_NAMES[dept], "years": [y0, y1], "maison": summary.get("maison"), "appartement": summary.get("appartement"),
                "communes": sorted(communes.values(), key=lambda c: -c["count"])}

    return await cached(f"dept:{dept}", build)


async def _insee_from_slug(dept: str, slug: str) -> str:
    """Résout un slug de commune (« cormeray », « saint-aignan ») en code INSEE au sein du département."""
    wanted = _slug(slug)
    data = await prices_dept(dept)
    hit = next((c for c in data["communes"] if c["slug"] == wanted), None)
    if not hit:
        raise HTTPException(status_code=404, detail="Commune inconnue dans ce département")
    return hit["insee"]


@router.get("/prices/{dept}/{insee}")
async def prices_commune(dept: str, insee: str):
    dept = dept.upper()
    if dept not in DEPT_NAMES:
        raise HTTPException(status_code=404, detail="Département inconnu")
    # Tolérance d'URL : « 41061-cormeray » (INSEE + slug) ou « cormeray » (slug seul) → code INSEE
    insee = insee.split("-")[0].upper() if insee[:1].isdigit() else await _insee_from_slug(dept, insee)
    y0, y1 = _years()

    async def build():
        base = {"code_commune": insee, "dept": dept}
        overall = await db.dvf_sales.aggregate([{"$match": {**base, "year": {"$gte": y0, "$lte": y1}}}, *_median_group({"type": "$type"})]).to_list(10)
        if not overall:
            raise HTTPException(status_code=404, detail="Commune sans vente enregistrée")
        by_year = await db.dvf_sales.aggregate([{"$match": {**base, "year": {"$gte": y1 - 5}}}, *_median_group({"type": "$type", "year": "$year"}),
                                                {"$sort": {"_id.year": 1}}]).to_list(50)
        recent = await db.dvf_sales.find({**base, "year": {"$gte": y0}}, {"_id": 0, "date": 1, "type": 1, "surface": 1, "rooms": 1, "land_surface": 1, "price": 1, "price_m2": 1}) \
            .sort("date", -1).limit(12).to_list(12)
        pop = await db.communes.find_one({"_id": insee}, {"population": 1, "nom": 1})
        dept_data = await prices_dept(dept)
        me = next((c for c in dept_data["communes"] if c["insee"] == insee), None)
        neighbours = [c for c in dept_data["communes"] if c["insee"] != insee and c["count"] >= MIN_SALES_SITEMAP][:10]
        return {
            "insee": insee, "dept": dept, "dept_name": DEPT_NAMES[dept], "name": (me or {}).get("name") or (pop or {}).get("nom") or overall[0]["commune"],
            "slug": (me or {}).get("slug") or _slug(overall[0]["commune"]), "code_postal": overall[0]["code_postal"], "population": (pop or {}).get("population"),
            "years": [y0, y1], "count": sum(r["count"] for r in overall),
            "maison": next((_fmt(r) for r in overall if r["_id"]["type"] == "maison"), None),
            "appartement": next((_fmt(r) for r in overall if r["_id"]["type"] == "appartement"), None),
            "dept_maison": dept_data["maison"], "dept_appartement": dept_data["appartement"],
            "trend": [{"type": r["_id"]["type"], "year": r["_id"]["year"], "median_pm2": round(r["median_pm2"]), "count": r["count"]} for r in by_year if r["count"] >= 3],
            "recent_sales": [{**r, "date": r["date"].strftime("%Y-%m"), "price_m2": round(r["price_m2"])} for r in recent],
            "neighbours": neighbours,
        }

    return await cached(f"commune:{dept}:{insee}", build)


STATIC_PAGES = ["/", "/accueil", "/estimation-maison", "/estimation-immobiliere", "/combien-vaut-ma-maison", "/vendre-sa-maison", "/conseils-vente", "/faq", "/prix-immobilier", "/privacy", "/mentions-legales", "/cgu"]


@router.get("/web-bundle.zip", include_in_schema=False)
async def web_bundle():
    """Kit du projet web séparé (webproject/ + export statique webdist/), généré par scripts/build-web.sh."""
    path = Path(__file__).parent / "web-bundle.zip"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Bundle non généré (scripts/build-web.sh)")
    return FileResponse(path, media_type="application/zip", filename="web-bundle.zip")


@router.get("/store-assets.zip", include_in_schema=False)
async def store_assets():
    """Visuels des fiches stores (icônes 512/1024, image de présentation 1024×500), générés par scripts/gen_store_assets.py."""
    path = Path(__file__).parent / "store-assets.zip"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Visuels non générés (scripts/gen_store_assets.py)")
    return FileResponse(path, media_type="application/zip", filename="achetemamaison-visuels-stores.zip")


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap(request: Request):
    """Plan du site : pages publiques + départements + communes avec assez de ventes. Référencé par /robots.txt."""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    base = f"{proto}://{host}"
    y0, y1 = _years()

    async def communes():
        rows = await db.dvf_sales.aggregate([{"$match": {"year": {"$gte": y0, "$lte": y1}}},
                                             {"$group": {"_id": {"dept": "$dept", "insee": "$code_commune"}, "n": {"$sum": 1}, "commune": {"$first": "$commune"}}},
                                             {"$match": {"n": {"$gte": MIN_SALES_SITEMAP}}}], allowDiskUse=True).to_list(40000)
        return [(r["_id"]["dept"], r["_id"]["insee"], _slug(r["commune"])) for r in rows]

    rows = await cached("sitemap-communes", communes)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [(f"{base}{p}", "weekly", "0.9" if p != "/privacy" else "0.2") for p in STATIC_PAGES]
    urls += [(f"{base}/prix-immobilier/{d}", "monthly", "0.7") for d in ALL_FRANCE]
    urls += [(f"{base}/prix-immobilier/{d}/{i}-{s}", "monthly", "0.5") for d, i, s in rows]
    body = "".join(f"<url><loc>{escape(u)}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>" for u, f, p in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=86400"})
