"""Atouts du quartier mesurés (analyse d'environnement) → faits utilisables par la rédaction d'annonce.

Uniquement des éléments positifs ou neutres, avec leur distance mesurée ; aucune nuisance n'est transformée en argument,
aucun qualificatif n'est ajouté. L'IA de rédaction ne peut citer que ces lignes, telles quelles.
"""
from __future__ import annotations

CATEGORY_LABEL = {"ecole": "école / établissement scolaire", "commerce": "commerce alimentaire", "pharmacie": "pharmacie", "sante": "professionnel ou établissement de santé",
                  "service_public": "service public", "sport": "équipement sportif", "culture": "équipement culturel"}
MAX_M = {"ecole": 1000, "commerce": 1000, "pharmacie": 1000, "sante": 1000, "service_public": 1000, "sport": 1000, "culture": 1000, "transport": 500, "gare": 2500,
         "green": 800, "water": 600, "forest": 800}


def _dist(m: int) -> str:
    return f"{m / 1000:.1f} km".replace(".", ",") if m >= 1000 else f"{int(round(m / 10.0) * 10)} m"


def _name(it: dict) -> str | None:
    n = it.get("name")
    return n.strip() if isinstance(n, str) and n.strip() else None


def neighbourhood_highlights(env: dict) -> list[dict]:
    """Liste ordonnée de {key, text, distance_m, source} — vide si rien de mesurable dans les seuils."""
    out: list[dict] = []
    services = env.get("services") or []
    for cat, label in CATEGORY_LABEL.items():
        items = [s for s in services if s.get("category") == cat and s["distance_m"] <= MAX_M[cat]]
        if not items:
            continue
        nearest = items[0]
        if cat == "commerce" and len(items) >= 2:
            text = f"{len(items)} commerces alimentaires à moins de {_dist(max(i['distance_m'] for i in items))} (le plus proche à {_dist(nearest['distance_m'])})"
        else:
            who = f"{_name(nearest)} ({label})" if _name(nearest) and cat != "sante" else label.capitalize()
            text = f"{who} à environ {_dist(nearest['distance_m'])}"
        out.append({"key": cat, "text": text, "distance_m": nearest["distance_m"], "source": nearest.get("source", "osm")})
    transport = env.get("transport") or []
    bus = [t for t in transport if t.get("category") == "transport" and t["distance_m"] <= MAX_M["transport"]]
    if bus:
        out.append({"key": "bus", "text": f"Arrêt de transport en commun à environ {_dist(bus[0]['distance_m'])}", "distance_m": bus[0]["distance_m"], "source": bus[0].get("source", "osm")})
    gares = [t for t in transport if (t.get("category") == "gare" or "Gare" in str(t.get("type"))) and t["distance_m"] <= MAX_M["gare"]]
    if gares:
        g = gares[0]
        out.append({"key": "gare", "text": f"{_name(g) or 'Gare'} à environ {_dist(g['distance_m'])}", "distance_m": g["distance_m"], "source": g.get("source", "bdtopo")})
    greens = [g for g in (env.get("green_spaces") or []) if g["distance_m"] <= MAX_M["green"]]
    if greens:
        g = greens[0]
        nat = (g.get("nature") or "espace vert").lower()
        out.append({"key": "vert", "text": f"{nat.capitalize()} à environ {_dist(g['distance_m'])}", "distance_m": g["distance_m"], "source": g.get("source", "bdtopo")})
    terrain = env.get("terrain") or {}
    water = [w for w in (env.get("water") or []) if w["distance_m"] <= MAX_M["water"] and w.get("name")]
    if water and not any(i.get("key") in ("inondation", "nappe") for i in ((env.get("risks") or {}).get("at_address") or [])):
        w = water[0]
        out.append({"key": "eau", "text": f"{w['name']} ({w.get('type', 'cours d’eau')}) à environ {_dist(w['distance_m'])}", "distance_m": w["distance_m"], "source": "bdtopo"})
    if terrain.get("nearest_forest_m") is not None and terrain["nearest_forest_m"] <= MAX_M["forest"] and not any(o["key"] == "vert" for o in out):
        out.append({"key": "foret", "text": f"Boisement à environ {_dist(terrain['nearest_forest_m'])}", "distance_m": terrain["nearest_forest_m"], "source": "bdtopo"})
    priority = ["ecole", "commerce", "gare", "bus", "vert", "eau", "pharmacie", "sante", "foret", "service_public", "sport", "culture"]
    out.sort(key=lambda x: (priority.index(x["key"]) if x["key"] in priority else 99, x["distance_m"]))
    return out[:5]


def facts_block(env: dict) -> str | None:
    hl = neighbourhood_highlights(env)
    if not hl:
        return None
    lines = "\n".join(f"- {h['text']}" for h in hl)
    return ("ATOUTS DU QUARTIER MESURÉS (distances à vol d'oiseau, sources publiques : IGN BD TOPO / OpenStreetMap). "
            "Tu peux les citer UNIQUEMENT tels quels, avec la distance indiquée (« à environ … »), sans aucun qualificatif "
            "(ni « proche », « idéalement situé », « calme », « recherché »). N'en déduis rien d'autre.\n" + lines)
