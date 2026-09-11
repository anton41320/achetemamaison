"""Commune populations (geo.api.gouv.fr) used to compare towns of similar size when widening the search radius."""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger("communes")

GEO_API = "https://geo.api.gouv.fr/communes"
_cache: dict[str, dict] = {}


def refresh_populations(mongo_url: str, db_name: str, departments: list[str]) -> int:
    """Download and upsert {code, nom, population, dept} for every commune of the configured departments."""
    from pymongo import MongoClient

    client = MongoClient(mongo_url)
    db = client[db_name]
    n = 0
    try:
        for dept in departments:
            try:
                r = requests.get(GEO_API, params={"codeDepartement": dept, "fields": "code,nom,population", "format": "json"}, timeout=20)
                r.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                logger.warning("geo.api.gouv.fr unavailable for %s: %s", dept, exc)
                continue
            for c in r.json():
                if not c.get("population"):
                    continue
                db.communes.replace_one({"_id": c["code"]}, {"_id": c["code"], "nom": c["nom"], "population": int(c["population"]), "dept": dept}, upsert=True)
                n += 1
        _cache.clear()
    finally:
        client.close()
    return n


async def load_populations(db) -> dict[str, dict]:
    if _cache:
        return _cache
    async for c in db.communes.find({}, {"nom": 1, "population": 1}):
        _cache[c["_id"]] = {"nom": c["nom"], "population": c["population"]}
    return _cache


def size_band(pop: int) -> str:
    if pop < 2000:
        return "village"
    if pop < 10000:
        return "bourg"
    if pop < 50000:
        return "petite ville"
    return "ville"
