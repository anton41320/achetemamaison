"""Ajustements d'estimation issus de l'environnement (micro-localisation), transparents et bornés.

Les comparables DVF captent déjà le niveau de prix du quartier ; ces ajustements ne traduisent que des facteurs
de micro-localisation mesurés par distance (sources BD TOPO / OSM / Géorisques). Total borné à [-6 %, +4 %].
"""
from __future__ import annotations

from models import Adjustment

CAP_LOW, CAP_HIGH = -0.06, 0.04


def _nearest(items: list[dict], pred=lambda x: True) -> int | None:
    ds = [i["distance_m"] for i in items if pred(i)]
    return min(ds) if ds else None


def environment_adjustments(env: dict, value_base: float) -> list[Adjustment]:
    out: list[tuple[str, str, float]] = []
    roads = env.get("roads") or []
    d = _nearest(roads, lambda r: r.get("importance") == "1")
    if d is not None and d <= 300:
        out.append(("env_autoroute", f"Axe autoroutier à {d} m (BD TOPO)", -0.03 if d <= 150 else -0.015))
    d = _nearest(roads, lambda r: r.get("importance") == "2")
    if d is not None and d <= 150:
        out.append(("env_axe_principal", f"Axe principal à {d} m (BD TOPO)", -0.02 if d <= 60 else -0.01))
    d = _nearest(env.get("railways") or [], lambda r: (r.get("nature") or "") != "Voie de service")
    if d is not None and d <= 300:
        out.append(("env_voie_ferree", f"Voie ferrée à {d} m (BD TOPO)", -0.02 if d <= 150 else -0.01))
    d = _nearest(env.get("industrial_sites") or [], lambda i: i.get("category") != "parking")
    if d is not None and d <= 300:
        out.append(("env_industrie", f"Zone d'activité industrielle ou commerciale à {d} m", -0.02 if d <= 150 else -0.01))
    d = _nearest(env.get("aerodromes") or [])
    if d is not None and d <= 5000:
        out.append(("env_aerodrome", f"Aérodrome à {d / 1000:.1f} km (BD TOPO)", -0.01))
    risks = env.get("risks") or {}
    flood = [i for i in risks.get("at_address") or [] if i.get("key") in ("inondation", "nappe") and i.get("level") in ("medium", "high")]
    if flood:
        out.append(("env_inondation", "Risque inondation / remontée de nappe recensé à l'adresse (Géorisques)", -0.03))
    if (risks.get("argile") or {}).get("level") == "high":
        out.append(("env_argile", "Exposition forte au retrait-gonflement des argiles (Géorisques)", -0.01))
    terrain = env.get("terrain") or {}
    dw = terrain.get("nearest_water_m")
    if dw is not None and dw <= 250 and not flood:
        out.append(("env_eau", f"Cours d'eau ou plan d'eau à {dw} m (BD TOPO)", 0.01))
    df = terrain.get("nearest_forest_m")
    green = env.get("green_spaces") or []
    dg = _nearest(green)
    if (df is not None and df <= 250) or (dg is not None and dg <= 250):
        out.append(("env_vert", f"Espace boisé ou parc à {min(x for x in (df, dg) if x is not None)} m", 0.015))
    services = env.get("services") or []
    if _nearest(services, lambda s: s.get("category") == "ecole") is not None and _nearest(services, lambda s: s.get("category") == "ecole") <= 500:
        out.append(("env_ecole", "École ou établissement d'enseignement à moins de 500 m", 0.01))
    shops = [s for s in services if s.get("category") == "commerce" and s["distance_m"] <= 500]
    if len(shops) >= 3:
        out.append(("env_commerces", f"{len(shops)} commerces alimentaires à moins de 500 m (OSM)", 0.01))
    transport = env.get("transport") or []
    if _nearest(transport, lambda t: t.get("category") == "transport") is not None and _nearest(transport, lambda t: t.get("category") == "transport") <= 300:
        out.append(("env_bus", "Arrêt de transport en commun à moins de 300 m (OSM)", 0.01))
    dgare = _nearest(transport, lambda t: t.get("category") == "gare" or "Gare" in str(t.get("type")))
    if dgare is not None and dgare <= 1000:
        out.append(("env_gare", f"Gare ou station à {dgare} m", 0.01))

    total = sum(p for _, _, p in out)
    cap = CAP_LOW if total < CAP_LOW else CAP_HIGH if total > CAP_HIGH else None
    scale = cap / total if cap is not None else 1.0
    adjs = [Adjustment(key=k, label=lbl, pct=round(p * scale, 4), amount=0.0) for k, lbl, p in out]
    if cap is not None and adjs:  # absorbe l'arrondi sur le dernier facteur pour respecter exactement la borne
        adjs[-1].pct = round(cap - sum(a.pct for a in adjs[:-1]), 4)
    for a in adjs:
        a.amount = round(value_base * a.pct)
    return adjs
