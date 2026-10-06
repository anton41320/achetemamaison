"""HTTP + cache commun à toutes les sources. Aucune donnée n'est inventée : un échec renvoie `None` et une
entrée `sources[]` avec `status="unavailable"`."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger("environment")

UA = {"User-Agent": "achetemamaison/1.0 (analyse environnement ; contact via l'application)", "Accept": "application/json"}
CACHE_DAYS = 30
_session = requests.Session()
_session.headers.update(UA)

# Registre des sources (documentation : voir /app/memory/environment_sources.md)
SOURCES: dict[str, dict] = {
    "ban": {"name": "Base Adresse Nationale (BAN)", "url": "https://adresse.data.gouv.fr/api-doc/adresse", "licence": "Licence Ouverte 2.0", "kind": "official"},
    "cadastre": {"name": "Cadastre — API Carto (IGN / DGFiP)", "url": "https://apicarto.ign.fr/api/doc/cadastre", "licence": "Licence Ouverte 2.0", "kind": "official"},
    "bdtopo": {"name": "IGN BD TOPO® (Géoplateforme WFS)", "url": "https://geoservices.ign.fr/bdtopo", "licence": "Licence Ouverte 2.0", "kind": "official"},
    "alti": {"name": "IGN RGE ALTI® (service altimétrique)", "url": "https://geoservices.ign.fr/services-geoplateforme-altimetrie", "licence": "Licence Ouverte 2.0", "kind": "official"},
    "clc": {"name": "Corine Land Cover 2018 (IGN / CGDD)", "url": "https://www.statistiques.developpement-durable.gouv.fr/corine-land-cover-0", "licence": "Licence Ouverte 2.0", "kind": "official", "precision": "unité minimale 25 ha"},
    "gpu": {"name": "Géoportail de l'Urbanisme (GPU)", "url": "https://www.geoportail-urbanisme.gouv.fr/", "licence": "Licence Ouverte 2.0", "kind": "official"},
    "georisques": {"name": "Géorisques (BRGM / MTE)", "url": "https://www.georisques.gouv.fr/", "licence": "Licence Ouverte 2.0", "kind": "official"},
    "osm": {"name": "OpenStreetMap (Overpass)", "url": "https://www.openstreetmap.org/copyright", "licence": "ODbL 1.0 — © les contributeurs OpenStreetMap", "kind": "open"},
}


def _key(source: str, url: str, params: Optional[dict], data: Optional[dict]) -> str:
    raw = json.dumps({"s": source, "u": url, "p": params or {}, "d": data or {}}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _get(url: str, params: Optional[dict], data: Optional[dict], timeout: int) -> Any:
    r = _session.post(url, data=data, timeout=timeout) if data is not None else _session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


async def fetch_json(db, source: str, url: str, *, params: Optional[dict] = None, data: Optional[dict] = None,
                     timeout: int = 20, retries: int = 1, cache_days: int = CACHE_DAYS) -> tuple[Any, dict]:
    """Returns (payload | None, source_record). Cached in Mongo `env_cache` (hash of url+params)."""
    key = _key(source, url, params, data)
    now = datetime.now(timezone.utc)
    cached = await db.env_cache.find_one({"_id": key}) if db is not None else None
    if cached and cached["fetched_at"].replace(tzinfo=timezone.utc) > now - timedelta(days=cache_days):
        return cached["payload"], {**_record(source, url, cached["fetched_at"]), "cached": True}
    payload, err = None, None
    for attempt in range(retries + 1):
        try:
            payload = await asyncio.to_thread(_get, url, params, data, timeout)
            break
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:160]
            logger.warning("%s %s failed (%d): %s", source, url.split("?")[0], attempt + 1, err)
            await asyncio.sleep(0.8 * (attempt + 1))
    if payload is None:
        if cached:  # stale but better than nothing — flagged
            return cached["payload"], {**_record(source, url, cached["fetched_at"]), "cached": True, "stale": True}
        return None, {**_record(source, url, now), "status": "unavailable", "error": err}
    if db is not None:
        await db.env_cache.replace_one({"_id": key}, {"_id": key, "source": source, "url": url, "fetched_at": now, "payload": payload}, upsert=True)
    return payload, _record(source, url, now)


def _record(source: str, url: str, fetched_at: datetime) -> dict:
    meta = SOURCES[source]
    return {"id": source, "name": meta["name"], "kind": meta["kind"], "licence": meta["licence"], "doc_url": meta["url"],
            "request_url": url, "fetched_at": fetched_at.isoformat() if isinstance(fetched_at, datetime) else fetched_at,
            "precision": meta.get("precision"), "status": "ok"}
