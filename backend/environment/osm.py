"""OpenStreetMap via Overpass : services, commerces, santé, transports (complément des sources officielles)."""
from __future__ import annotations

from typing import Optional

from environment.sources import fetch_json

OVERPASS_URLS = ["https://overpass.openstreetmap.fr/api/interpreter", "https://overpass-api.de/api/interpreter"]

# catégorie → (clé OSM, valeurs)
CATEGORIES = {
    "ecole": ("amenity", ["school", "kindergarten", "college", "university"]),
    "sante": ("amenity", ["doctors", "clinic", "hospital", "dentist"]),
    "pharmacie": ("amenity", ["pharmacy"]),
    "commerce": ("shop", ["supermarket", "convenience", "bakery", "butcher", "greengrocer", "mall", "department_store"]),
    "service_public": ("amenity", ["townhall", "post_office", "police", "library"]),
    "transport": ("highway", ["bus_stop"]),
    "gare": ("railway", ["station", "halt", "tram_stop"]),
    "sport": ("leisure", ["sports_centre", "pitch", "swimming_pool", "stadium", "fitness_centre"]),
    "espace_vert": ("leisure", ["park", "garden", "playground", "nature_reserve"]),
    "nuisance": ("amenity", ["nightclub", "bar", "fuel"]),
    "industrie": ("landuse", ["industrial", "quarry", "landfill"]),
}
LABELS = {"ecole": "Écoles et enseignement", "sante": "Santé", "pharmacie": "Pharmacies", "commerce": "Commerces alimentaires", "service_public": "Services publics",
          "transport": "Arrêts de bus", "gare": "Gares et stations", "sport": "Équipements sportifs", "espace_vert": "Parcs et jardins",
          "nuisance": "Établissements potentiellement bruyants (bars, boîtes de nuit, stations-service)", "industrie": "Zones industrielles / carrières (OSM)"}


def _query(lat: float, lon: float, radius_m: int) -> str:
    parts = []
    for key, values in CATEGORIES.values():
        regex = "|".join(values)
        parts.append(f'nwr["{key}"~"^({regex})$"](around:{radius_m},{lat:.6f},{lon:.6f});')
    return f"[out:json][timeout:25];({''.join(parts)});out center tags 400;"


async def pois(db, lon: float, lat: float, radius_m: int) -> tuple[Optional[list[dict]], dict]:
    rec = None
    for url in OVERPASS_URLS:
        payload, rec = await fetch_json(db, "osm", url, data={"data": _query(lat, lon, radius_m)}, timeout=35)
        if payload is not None:
            break
    if payload is None:
        return None, rec
    out = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        c = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        if c.get("lat") is None:
            continue
        cat = next((k for k, (key, values) in CATEGORIES.items() if tags.get(key) in values), None)
        if not cat:
            continue
        out.append({"id": f"{el.get('type')}/{el.get('id')}", "category": cat, "name": tags.get("name"), "osm_tag": f"{CATEGORIES[cat][0]}={tags.get(CATEGORIES[cat][0])}",
                    "lon": c["lon"], "lat": c["lat"], "url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}"})
    return out, rec
