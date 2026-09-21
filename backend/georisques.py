"""Géorisques (API publique V1, sans clé) — risques naturels et technologiques autour d'un bien.

Agrège le rapport « connaître les risques près de chez moi », l'exposition argile (RGA), le potentiel radon,
les arrêtés CatNat de la commune et les installations classées à proximité. Résultat normalisé et mis en
cache 30 jours par bien (collection `risks`). Information publique : gratuite pour tous les utilisateurs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger("georisques")

BASE = "https://georisques.gouv.fr/api/v1"
CACHE_DAYS = 30
ICPE_RADIUS_M = 1000
_session = requests.Session()
_session.headers.update({"Accept": "application/json", "User-Agent": "achetesmamaison/1.0", "Connection": "close"})

# key in rapport -> (our key, short label, family)
NATURAL = {
    "inondation": ("inondation", "Inondation", "naturel"),
    "remonteeNappe": ("nappe", "Remontée de nappe", "naturel"),
    "seisme": ("seisme", "Séisme", "naturel"),
    "mouvementTerrain": ("mouvement_terrain", "Mouvements de terrain", "naturel"),
    "retraitGonflementArgile": ("argile", "Retrait-gonflement des argiles", "naturel"),
    "radon": ("radon", "Radon", "naturel"),
    "feuForet": ("feu_foret", "Feu de forêt", "naturel"),
    "risqueCotier": ("cotier", "Risques côtiers", "naturel"),
    "avalanche": ("avalanche", "Avalanche", "naturel"),
    "cavite": ("cavite", "Cavités souterraines", "naturel"),
}
TECH = {
    "icpe": ("icpe", "Installations industrielles (ICPE)", "technologique"),
    "nucleaire": ("nucleaire", "Nucléaire", "technologique"),
    "canalisationsMatieresDangereuses": ("canalisations", "Canalisations de matières dangereuses", "technologique"),
    "pollutionSols": ("pollution_sols", "Pollution des sols", "technologique"),
    "ruptureBarrage": ("barrage", "Rupture de barrage", "technologique"),
    "risqueMinier": ("minier", "Risque minier", "technologique"),
}
RADON_LABELS = {"1": ("low", "Potentiel faible"), "2": ("medium", "Potentiel moyen"), "3": ("high", "Potentiel significatif")}
ARGILE_LABELS = {"0": ("none", "Exposition nulle"), "1": ("low", "Exposition faible"), "2": ("medium", "Exposition moyenne"),
                 "3": ("high", "Exposition forte")}


def _get(path: str, params: dict, timeout: int = 20) -> Optional[dict]:
    import time

    for attempt in range(3):
        try:
            r = _session.get(f"{BASE}{path}", params=params, timeout=timeout)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Géorisques %s failed (attempt %d): %s", path, attempt + 1, exc)
            time.sleep(1.0 * (attempt + 1))
    return None


def _level(status: Optional[str], present: bool) -> str:
    s = (status or "").lower()
    if not present or "non" in s and "connu" in s and "existant" not in s:
        return "none"
    if "important" in s or "fort" in s or "élevé" in s:
        return "high"
    if "moyen" in s or "modéré" in s:
        return "medium"
    if "faible" in s:
        return "low"
    if "existant" in s or "concern" in s:
        return "medium"
    return "info"


def fetch(lat: float, lon: float, code_insee: str) -> dict:
    """Synchronous aggregation (run in a thread). Never raises: partial data is returned with `partial=True`."""
    latlon = f"{lon:.5f},{lat:.5f}"  # Géorisques attend longitude,latitude
    from concurrent.futures import ThreadPoolExecutor

    calls = {
        "rapport": ("/resultats_rapport_risque", {"latlon": latlon}),
        "rga": ("/rga", {"latlon": latlon}),
        "radon": ("/radon", {"code_insee": code_insee, "page": 1, "page_size": 5}),
        "catnat": ("/gaspar/catnat", {"code_insee": code_insee, "page": 1, "page_size": 100}),
        "icpe": ("/installations_classees", {"latlon": latlon, "rayon": ICPE_RADIUS_M, "page": 1, "page_size": 20}),
    }
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {k: pool.submit(_get, path, params) for k, (path, params) in calls.items()}
        res = {k: f.result() for k, f in futures.items()}
    rapport, rga, radon, catnat, icpe = res["rapport"], res["rga"], res["radon"], res["catnat"], res["icpe"]
    partial = any(x is None for x in (rapport, rga, radon, catnat))

    items: list[dict] = []
    for fam, mapping in (("risquesNaturels", NATURAL), ("risquesTechnologiques", TECH)):
        for src_key, (key, label, family) in mapping.items():
            r = ((rapport or {}).get(fam) or {}).get(src_key)
            if not r:
                continue
            addr = r.get("libelleStatutAdresse") or ""
            at_address = bool(addr) and "inconnu" not in addr.lower() and "non connu" not in addr.lower()
            present = bool(r.get("present"))
            # Known at the address itself -> graded level ; only recorded at commune level -> "info".
            level = _level(addr, present) if at_address else ("info" if present else "none")
            items.append({"key": key, "label": r.get("libelle") or label, "family": family, "present": present,
                          "scope": "adresse" if at_address else "commune",
                          "status_address": r.get("libelleStatutAdresse"), "status_commune": r.get("libelleStatutCommune"),
                          "level": level})

    argile_code = str((rga or {}).get("codeExposition") or "")
    argile_level, argile_label = ARGILE_LABELS.get(argile_code, ("info", (rga or {}).get("exposition") or "Non renseigné"))
    radon_row = ((radon or {}).get("data") or [{}])[0]
    radon_code = str(radon_row.get("classe_potentiel") or "")
    radon_level, radon_label = RADON_LABELS.get(radon_code, ("info", "Non renseigné"))

    events = (catnat or {}).get("data") or []
    by_type: dict[str, int] = {}
    for e in events:
        t = e.get("libelle_risque_jo") or "Autre"
        by_type[t] = by_type.get(t, 0) + 1

    def _key(e):
        d = e.get("date_debut_evt") or ""
        return d[6:10] + d[3:5] + d[0:2]

    last = [{"type": e.get("libelle_risque_jo"), "start": e.get("date_debut_evt"), "end": e.get("date_fin_evt")}
            for e in sorted(events, key=_key, reverse=True)[:5]]
    sites = [{"name": s.get("raisonSociale") or s.get("nomEts") or "Installation", "regime": s.get("regime") or s.get("libRegime"),
              "seveso": s.get("statutSeveso") or s.get("seveso")} for s in ((icpe or {}).get("data") or [])[:6]]

    for it in items:  # enrich the two graded risks with their precise exposure
        if it["key"] == "argile":
            it["level"], it["detail"] = argile_level, argile_label
        if it["key"] == "radon":
            it["level"], it["detail"] = radon_level, radon_label
    return {
        "fetched_at": datetime.now(timezone.utc),
        "partial": partial,
        "source_url": (rapport or {}).get("url") or "https://www.georisques.gouv.fr/",
        "commune": (rapport or {}).get("commune") or {"codeInsee": code_insee},
        "items": items,
        "argile": {"code": argile_code, "level": argile_level, "label": argile_label},
        "radon": {"code": radon_code, "level": radon_level, "label": radon_label},
        "catnat": {"count": int((catnat or {}).get("results") or len(events)), "by_type": by_type, "last": last},
        "icpe": {"count": int((icpe or {}).get("results") or 0), "radius_m": ICPE_RADIUS_M, "sites": sites},
        "dossier_flags": {
            "erp_required": True,
            "geotechnique_required": argile_code in ("2", "3"),
            "radon_significant": radon_code == "3",
            "catnat_secheresse": any("cheresse" in t for t in by_type),
        },
    }


def summary_lines(risks: dict) -> list[str]:
    """Short French sentences for PDFs and the ERP checklist reason."""
    lines = []
    present = [it for it in risks.get("items", []) if it.get("present") and it.get("level") not in ("none",)]
    at_addr = [it for it in present if it.get("scope") == "adresse"]
    commune_only = [it for it in present if it.get("scope") != "adresse"]
    if at_addr:
        lines.append("À l'adresse : " + ", ".join(
            f"{it['label'].lower()}" + (f" ({it['detail'].lower()})" if it.get("detail") else "") for it in at_addr) + ".")
    if commune_only:
        lines.append("Recensés sur la commune : " + ", ".join(it["label"].lower() for it in commune_only) + ".")
    if not present:
        lines.append("Aucun risque recensé à cette adresse dans le rapport Géorisques.")
    c = risks.get("catnat") or {}
    if c.get("count"):
        top = sorted((c.get("by_type") or {}).items(), key=lambda kv: -kv[1])[:3]
        lines.append(f"{c['count']} arrêté(s) de catastrophe naturelle sur la commune (" + ", ".join(f"{t.lower()} ×{n}" for t, n in top) + ").")
    i = risks.get("icpe") or {}
    if i.get("count"):
        lines.append(f"{i['count']} installation(s) classée(s) dans un rayon de {i.get('radius_m', 1000)} m.")
    return lines


async def get_for_property(db, prop, force: bool = False) -> dict:
    """Cached Géorisques snapshot for a property (30 days)."""
    import asyncio

    cached = await db.risks.find_one({"_id": prop.id})
    fresh = cached and cached.get("fetched_at") and cached["fetched_at"].replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) - timedelta(days=CACHE_DAYS)
    if cached and fresh and not force and not cached.get("partial"):
        return cached
    data = await asyncio.to_thread(fetch, prop.lat, prop.lon, prop.code_commune)
    if data["partial"] and cached:  # keep the better snapshot rather than a degraded one
        return cached
    await db.risks.replace_one({"_id": prop.id}, {"_id": prop.id, "property_id": prop.id, **data}, upsert=True)
    return {"_id": prop.id, "property_id": prop.id, **data}


def to_json(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(out.get("fetched_at"), datetime):
        out["fetched_at"] = out["fetched_at"].isoformat()
    return out
