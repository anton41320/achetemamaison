"""Phase 1 estimation engine: weighted DVF comparables with explicit confidence.

Rules
- Search radius widens automatically: 500 m -> quartier (1,5 km) -> commune -> secteur (5 km).
- Never returns a bare price: always a range whose width follows dispersion and confidence.
- If fewer than MIN_VIABLE comparables exist, the range is widened and flagged.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import communes
from models import (Adjustment, Comparable, Confidence, ConfidenceDetail, Estimation,
                    MarketLevel)

MIN_COMPS = 12
MIN_VIABLE = 3
LOOKBACK_YEARS = 5
MARKET_YEARS = 3
SEARCH_RADIUS_M = 10000
SIZE_RATIO = (0.4, 2.5)  # a commune is "of similar size" when its population is within 0,4× – 2,5× the target's
TIGHT_TOL = 0.15  # surface tolerance tried first at each radius (less price/m² dispersion)
OUTBUILDING_LABELS = {"bureau": "Bureau indépendant", "hangar": "Hangar", "grange": "Grange", "abri_jardin": "Abri de jardin", "pool_house": "Pool house", "autre": "Dépendance"}
# Travaux déclarés : décote par poste (ordre de grandeur du coût rapporté à la valeur d'une maison type), total plafonné à -10 %.
WORKS_ADJ = {"toiture": ("toiture", -0.04), "assainissement": ("assainissement", -0.02), "electricite": ("électricité", -0.02),
             "rafraichissement": ("rafraîchissement", -0.015), "autre": ("autre", -0.01)}
RANGE_HALF = 0.05  # fourchette affichée : ±5 % autour de la valeur centrale (choix produit) ; l'incertitude réelle est portée par la dispersion
SIZE_ELASTICITY = 0.20  # price/m² ∝ surface^-0.20 (hedonic log-surface coefficient ≈ 0.80)
METHOD_VERSION = "comparables_dvf_v6"  # bump when the range/selection/hedonic logic changes: stored estimations auto-refresh

# (label, radius_m or None = same commune, surface tolerance, restrict to communes of similar size)
LEVELS = [
    ("À 500 m", 500, 0.30, False),
    ("Quartier (1,5 km)", 1500, 0.30, False),
    ("Commune", None, 0.35, False),
    ("5 km, communes similaires", 5000, 0.35, True),
    ("10 km, communes similaires", 10000, 0.35, True),
]

# Relatif à la vente DVF « typique » (bien habitable, en état correct à bon) : seuls les écarts à ce standard comptent.
CONDITION_ADJ = {
    "a_renover": (-0.15, "À rénover"),
    "travaux": (-0.08, "Travaux à prévoir"),
    "correct": (-0.02, "État correct"),
    "bon": (0.0, "Bon état (état de la vente type)"),
    "tres_bon": (0.04, "Très bon état"),
    "neuf_renove": (0.10, "Neuf / rénové"),
}
RENOVATED_OLD_PCT = 0.06  # « rénové » sur un bâti de plus de 15 ans : la structure et l'agencement restent d'époque

# Époque de construction (maison / appartement) : performance énergétique, normes, agencement — relatif au parc vendu,
# majoritairement construit avant 1990. Si un DPE est renseigné, la part « énergie » est déjà mesurée : effet réduit de 40 %.
YEAR_ADJ = {
    "maison": [(1950, -0.05, "Construction ancienne (avant 1950)"), (1975, -0.09, "Construction 1950–1974 (isolation, normes d'époque)"),
               (1990, -0.06, "Construction 1975–1989 (performance énergétique)"), (2005, -0.02, "Construction 1990–2004"),
               (2013, 0.05, "Construction 2005–2012 (RT 2005)"), (9999, 0.10, "Construction récente (RT 2012 et après)")],
    "appartement": [(1950, 0.0, "Immeuble ancien (avant 1950)"), (1975, -0.07, "Construction 1950–1974 (isolation, normes d'époque)"),
                    (1990, -0.05, "Construction 1975–1989 (performance énergétique)"), (2005, -0.01, "Construction 1990–2004"),
                    (2013, 0.04, "Construction 2005–2012 (RT 2005)"), (9999, 0.08, "Construction récente (RT 2012 et après)")],
}
# Maison récente (≤ 15 ans) : dans les secteurs où le parc vendu est ancien et bon marché, la décote « ancien » du marché ne
# s'applique pas à une construction neuve, dont la valeur reste adossée à son coût de construction actuel (maison + terrain
# courant, hors frais) : ≈ 2 000 €/m² en 2025–2026, amorti de 1,5 %/an. La prime « récent » est alors relevée jusqu'à ce
# plancher (bornée à +45 %), ce qui évite de sous-estimer un bien neuf comparé à des maisons des années 1960–1980.
NEW_BUILD_FLOOR_PM2, NEW_BUILD_DEPRECIATION, NEW_BUILD_MAX_AGE, NEW_BUILD_MAX_PCT = 2000.0, 0.015, 15, 0.45
# État + équipements déclarés (hors époque de construction, terrain et environnement) : la vente DVF « typique » est déjà
# une maison habitable et équipée ; une rénovation complète avec tous les équipements vaut en pratique +10 à +12 % au plus
# par rapport à elle. Au-delà, chaque ligne est réduite proportionnellement (les moins-values restent possibles jusqu'à −35 %).
DECLARED_MAX_UP, DECLARED_MAX_DOWN = 0.12, -0.35


def year_adjustment(ptype: str, year_built: Optional[int], has_dpe: bool) -> Optional[Adjustment]:
    if not year_built:
        return None
    for upper, pct, label in YEAR_ADJ.get(ptype, YEAR_ADJ["maison"]):
        if year_built < upper:
            if has_dpe:
                pct = round(pct * 0.6, 4)
            return Adjustment(key="year", label=label, pct=pct, amount=0.0)
    return None

LAND_PRICE_PER_M2 = 12.0            # excédent de terrain jusqu'à LAND_FULL_PRICE_M2 au-delà de la médiane locale
LAND_EXTRA_PRICE_PER_M2 = 3.0       # au-delà : terrain d'agrément, valorisé beaucoup moins (zones rurales)
LAND_FULL_PRICE_M2 = 500.0
LAND_CAP_UP = 0.04                  # un grand terrain ne fait pas une maison chère : bonus plafonné à +4 %
LAND_CAP_DOWN = 0.10

# Declared feature adjustments (transparent, bounded). DVF has none of these, so they are applied as explicit
# multiplicative corrections and listed one by one — relative to the typical sold house, which already has a garage,
# a terrace, a fenced plot… : standard equipment weighs little, premium equipment (pool, PAC, DPE A/B) a bit more,
# and real drawbacks (fioul, fosse, DPE F/G) keep their full weight.
FEATURE_MAX_UP, FEATURE_MAX_DOWN = 0.10, -0.25


def feature_adjustments(ptype: str, f, value_base: float, surface: Optional[float] = None) -> list[Adjustment]:
    out: list[tuple[str, str, float]] = []
    if f is None:
        return []
    maison = ptype == "maison"
    if f.pool == "hors_sol":
        out.append(("feat_pool", "Piscine hors-sol", 0.01))
    elif f.pool == "enterree":
        out.append(("feat_pool", "Piscine enterrée", 0.04))
    # terrain clos, portail motorisé, double vitrage, cellier, dressing : équipements de la maison type → neutres
    if f.terrace:
        out.append(("feat_terrace", "Terrasse", 0.005))
    if maison and f.garage == "aucun":
        out.append(("feat_garage", "Sans garage", -0.02))
    elif maison and f.garage == "deux_plus":
        out.append(("feat_garage", "Double garage ou plus", 0.02))
    if maison and f.outbuilding:
        label = OUTBUILDING_LABELS.get(f.outbuilding_type or "", "Dépendance")
        surf = f.outbuilding_surface or 0
        pct = 0.01 if f.outbuilding_type == "abri_jardin" else 0.02
        if surf >= 100:
            pct += 0.02
        elif surf >= 40:
            pct += 0.01
        out.append(("feat_outbuilding", label + (f" {surf:g} m²" if surf else ""), pct))
    if f.orientation in ("sud", "sud_ouest", "sud_est"):
        out.append(("feat_orientation", "Exposition sud", 0.01))
    elif f.orientation == "nord":
        out.append(("feat_orientation", "Exposition nord", -0.02))
    if maison and f.single_storey:
        out.append(("feat_single_storey", "Plain-pied", 0.02))
    if maison and f.basement:
        out.append(("feat_basement", "Sous-sol / cave", 0.005))
    if maison and f.convertible_attic:
        out.append(("feat_attic", "Combles aménageables", 0.005))
    if maison and f.master_suite:
        extras = [lbl for flag, lbl in ((f.master_suite_dressing, "dressing"), (f.master_suite_bathroom, "salle d'eau"), (f.master_suite_wc, "WC")) if flag]
        out.append(("feat_master_suite", "Suite parentale" + (f" ({', '.join(extras)})" if extras else ""), 0.01 + 0.005 * len(extras)))
    if f.bathrooms is not None and f.bathrooms >= 2:
        out.append(("feat_bathrooms", f"{f.bathrooms} salles de bain", 0.01))
    heating = {"pompe_a_chaleur": ("Pompe à chaleur", 0.02), "electrique": ("Chauffage électrique", -0.02),
               "fioul": ("Chauffage au fioul", -0.04)}
    if f.heating in heating:
        label, pct = heating[f.heating]
        out.append(("feat_heating", label, pct))
    sanitation = {"fosse_septique": ("Fosse septique (assainissement non collectif)", -0.02),
                  "fosse_toutes_eaux": ("Fosse toutes eaux (assainissement non collectif)", -0.01),
                  "microstation": ("Micro-station d'épuration", -0.005)}
    if ptype == "maison" and getattr(f, "sanitation", None) in sanitation:
        label, pct = sanitation[f.sanitation]
        out.append(("feat_sanitation", label, pct))
    dpe = {"A": 0.06, "B": 0.06, "C": 0.03, "D": 0.0, "E": -0.04, "F": -0.09, "G": -0.14}
    if f.dpe in dpe and dpe[f.dpe] != 0:
        out.append(("feat_dpe", f"DPE {f.dpe}", dpe[f.dpe]))
    if f.air_conditioning:
        out.append(("feat_ac", "Climatisation", 0.01))
    if f.fireplace and f.fireplace != "aucune":
        fire = {"insert": ("Cheminée avec insert", 0.01), "foyer_ouvert": ("Cheminée à foyer ouvert", 0.0),
                "poele_bois": ("Poêle à bois", 0.01), "poele_granules": ("Poêle à granulés", 0.01)}[f.fireplace]
        out.append(("feat_fireplace", *fire))
    if f.solar_panels:
        out.append(("feat_solar", "Panneaux solaires", 0.01))
    if not maison:
        if f.floor is not None:
            if f.floor == 0:
                out.append(("feat_floor", "Rez-de-chaussée", -0.03))
            elif f.floor >= 3 and f.elevator is False:
                out.append(("feat_floor", f"{f.floor}e étage sans ascenseur", -0.04))
            elif f.floor >= 2 and f.elevator:
                out.append(("feat_floor", f"{f.floor}e étage avec ascenseur", 0.02))
        if f.top_floor and (f.floor or 0) >= 1:
            out.append(("feat_top_floor", "Dernier étage", 0.03))
        if f.balcony:
            out.append(("feat_balcony", "Balcon / terrasse", 0.03))
        if f.parking == "garage":
            out.append(("feat_parking", "Garage fermé", 0.06))
        elif f.parking == "interieur":
            out.append(("feat_parking", "Parking intérieur / box", 0.05))
        elif f.parking == "exterieur":
            out.append(("feat_parking", "Parking extérieur", 0.03))
        if f.cellar:
            out.append(("feat_cellar", "Cave", 0.01))
        if f.caretaker:
            out.append(("feat_caretaker", "Gardien / concierge", 0.01))
        if f.heating_mode == "collectif":
            out.append(("feat_heating_mode", "Chauffage collectif", -0.01))
        if f.underfloor_heating:
            out.append(("feat_underfloor", "Chauffage au sol", 0.01))
        if f.condo_fees is not None and surface:
            per_m2 = f.condo_fees / surface  # €/m²/mois ; typique 2–3,5 €/m²/mois
            fees = f"{f.condo_fees:g} €/mois"
            if per_m2 > 5:
                out.append(("feat_condo_fees", f"Charges de copropriété élevées ({fees})", -0.04))
            elif per_m2 > 3.5:
                out.append(("feat_condo_fees", f"Charges de copropriété supérieures à la moyenne ({fees})", -0.02))
            elif per_m2 <= 2:
                out.append(("feat_condo_fees", f"Charges de copropriété modérées ({fees})", 0.01))
    if f.veranda:
        surf = f.veranda_surface or 0
        extras = [lbl for flag, lbl in ((f.veranda_heated, "chauffée"), (f.veranda_air_conditioned, "climatisée")) if flag]
        pct = 0.01 + (0.005 if surf >= 15 else 0) + (0.005 if f.veranda_heated else 0)
        out.append(("feat_veranda", "Véranda" + (f" {surf:g} m²" if surf else "") + (f" ({', '.join(extras)})" if extras else ""), pct))
    if f.works:
        items = [w for w in (f.works_items or []) if w in WORKS_ADJ]
        if items:
            pct = max(-0.10, sum(WORKS_ADJ[w][1] for w in items))
            labels = [WORKS_ADJ[w][0] if w != "autre" or not f.works_other else f"autre : {f.works_other.strip()}" for w in items]
            out.append(("feat_works", "Travaux à prévoir — " + ", ".join(labels), pct))
    out = [(k, lbl, p) for k, lbl, p in out if p != 0]
    total = sum(p for _, _, p in out)
    cap = FEATURE_MAX_UP if total > 0 else FEATURE_MAX_DOWN
    scale = min(1.0, abs(cap) / abs(total)) if abs(total) > abs(cap) else 1.0
    return [Adjustment(key=k, label=lbl, pct=round(p * scale, 4), amount=value_base * p * scale) for k, lbl, p in out]


class NoDataError(Exception):
    pass


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def median(vals: list[float]) -> float:
    return percentile(sorted(vals), 0.5)


def weighted_median(values: list[float], weights: list[float]) -> float:
    pairs = sorted(zip(values, weights))
    total = sum(weights)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= total / 2:
            return v
    return pairs[-1][0]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def round_to(x: float, step: int) -> float:
    return float(int(round(x / step)) * step)


async def fetch_candidates(db, lat: float, lon: float, code_commune: str, ptype: str,
                           exclude_mutation_id: Optional[str]) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=365 * LOOKBACK_YEARS)
    proj = {"mutation_id": 1, "date": 1, "price": 1, "surface": 1, "rooms": 1, "land_surface": 1,
            "price_m2": 1, "commune": 1, "code_commune": 1, "type": 1, "location": 1}
    base = {"type": ptype, "date": {"$gte": since}}
    if exclude_mutation_id:
        base["mutation_id"] = {"$ne": exclude_mutation_id}
    near_q = {**base, "location": {"$nearSphere": {
        "$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": SEARCH_RADIUS_M}}}
    near = await db.dvf_sales.find(near_q, proj).to_list(6000)
    commune = await db.dvf_sales.find({**base, "code_commune": code_commune}, proj).to_list(3000)
    seen: dict = {}
    for c in near + commune:
        seen[c["_id"]] = c
    now = datetime.now(timezone.utc)
    out = []
    for c in seen.values():
        clon, clat = c["location"]["coordinates"]
        c["distance_m"] = haversine_m(lat, lon, clat, clon)
        d = c["date"] if c["date"].tzinfo else c["date"].replace(tzinfo=timezone.utc)
        c["age_years"] = (now - d).days / 365.25
        out.append(c)
    return out


def _in_scope(c: dict, radius: Optional[int], code_commune: str, similar_only: bool = False) -> bool:
    if radius is None:
        return c["code_commune"] == code_commune
    if c["distance_m"] > radius:
        return False
    return c.get("similar_size", True) if similar_only else True


def _weight(c: dict, surface: float) -> float:
    w_time = 0.5 ** (c["age_years"] / 2.0)
    w_dist = 1.0 / (1.0 + c["distance_m"] / 1000.0)
    w_surf = math.exp(-((math.log(c["surface"] / surface)) / 0.25) ** 2)
    w_size = c.get("size_weight", 1.0)
    return w_time * w_dist * max(w_surf, 0.05) * w_size


def _trim_outliers(comps: list[dict]) -> list[dict]:
    if len(comps) < 6:
        return comps
    vals = sorted(c["pm2_adj"] for c in comps)
    q1, q3 = percentile(vals, 0.25), percentile(vals, 0.75)
    iqr = q3 - q1
    k = 1.0 if len(comps) >= 12 else 1.5  # stricter with many candidates: DVF mixes ruins, garages, renovated homes
    lo, hi = q1 - k * iqr, q3 + k * iqr
    kept = [c for c in comps if lo <= c["pm2_adj"] <= hi]
    return kept if len(kept) >= max(MIN_VIABLE, MIN_COMPS if len(comps) >= MIN_COMPS else 0) else comps


def _rel_iqr(comps: list[dict]) -> float:
    vals = sorted(c["pm2_adj"] for c in comps)
    med = median(vals)
    return (percentile(vals, 0.75) - percentile(vals, 0.25)) / med if len(vals) >= 2 and med else 0.5


def _se_median(comps: list[dict], weights: list[float]) -> float:
    """Relative sampling error of the weighted median: robust sd (IQR/1.349) × 1.2533 / sqrt(Kish effective n)."""
    n_eff = (sum(weights) ** 2) / sum(w * w for w in weights) if weights else 1.0
    return 1.2533 * (_rel_iqr(comps) / 1.349) / math.sqrt(max(n_eff, 1.0))


def _market(cands: list[dict], code_commune: str) -> list[MarketLevel]:
    recent = [c for c in cands if c["age_years"] <= MARKET_YEARS]
    out = []
    for label, radius, _, similar in LEVELS[:4]:
        sel = [c["price_m2"] for c in recent if _in_scope(c, radius, code_commune, similar)]
        out.append(MarketLevel(label=label, radius_m=radius, count=len(sel),
                               median_pm2=round_to(median(sel), 10) if sel else None))
    return out


def _tag_commune_size(cands: list[dict], code_commune: str, populations: dict) -> Optional[int]:
    """Mark each sale as coming from a commune of similar size (population ratio band) and set a soft weight."""
    target = (populations.get(code_commune) or {}).get("population")
    for c in cands:
        pop = (populations.get(c["code_commune"]) or {}).get("population")
        c["population"] = pop
        if c["code_commune"] == code_commune or not target or not pop:
            c["similar_size"], c["size_weight"] = True, 1.0
            continue
        ratio = pop / target
        c["similar_size"] = SIZE_RATIO[0] <= ratio <= SIZE_RATIO[1]
        c["size_weight"] = max(0.3, math.exp(-((math.log(ratio)) / 0.8) ** 2))
    return target


def estimate_from_candidates(cands: list[dict], *, surface: float, ptype: str, condition: str,
                             year_built: Optional[int], land_surface: Optional[float],
                             code_commune: str, features=None, populations: Optional[dict] = None) -> Estimation:
    notes: list[str] = []
    selected: list[dict] = []
    level_label = LEVELS[-1][0]
    tight_used = False
    target_pop = _tag_commune_size(cands, code_commune, populations or {})

    # Size-adjusted price/m²: every sale is brought to the target surface (price/m² falls with size).
    for c in cands:
        ratio = clamp(c["surface"] / surface, 0.5, 2.0)
        c["pm2_adj"] = c["price_m2"] * ratio ** SIZE_ELASTICITY

    def _prepared(sel: list[dict]) -> tuple[list[dict], list[float], float]:
        comps_ = _trim_outliers(sel)
        w_ = [_weight(c, surface) for c in comps_]
        return comps_, w_, _se_median(comps_, w_)

    # Walk the radii outward; once a level is viable, keep widening only while it pins the central value better
    # (weighted-median standard error at least 5 % lower): far sales in similar-sized communes add robustness
    # without drowning local information thanks to distance / size weighting.
    best: Optional[tuple[float, int, list[dict], bool]] = None
    for idx, (label, radius, tol, similar) in enumerate(LEVELS):
        in_scope = [c for c in cands if _in_scope(c, radius, code_commune, similar)]
        tight = [c for c in in_scope if (1 - TIGHT_TOL) * surface <= c["surface"] <= (1 + TIGHT_TOL) * surface]
        wide = [c for c in in_scope if (1 - tol) * surface <= c["surface"] <= (1 + tol) * surface]
        sel, is_tight = wide, False
        if len(tight) >= MIN_COMPS and len(wide) >= MIN_COMPS and _prepared(tight)[2] < _prepared(wide)[2]:
            sel, is_tight = tight, True
        if len(sel) < MIN_COMPS:
            if idx == len(LEVELS) - 1 and best is None:
                selected, level_label = sel, label
            continue
        se = _prepared(sel)[2]
        if best is None or se < best[0] * 0.95:
            best = (se, idx, sel, is_tight)
    if best is not None:
        _, idx, selected, tight_used = best
        label, radius, _, similar = LEVELS[idx]
        level_label = label
        if idx > 0:
            if similar and target_pop:
                notes.append(f"Rayon élargi à {radius // 1000} km en ne retenant que les communes de taille comparable "
                             f"à la vôtre ({target_pop:,} hab.) : base de ventes plus robuste.".replace(",", "\u202f"))
            else:
                notes.append(f"Peu de ventes comparables à 500 m : rayon élargi ({label.lower()}).")

    insufficient = False
    if len(selected) < MIN_VIABLE:
        # Drop the surface and size filters: use every sale of this type within 10 km / the commune.
        selected = [c for c in cands if _in_scope(c, SEARCH_RADIUS_M, code_commune) or c["code_commune"] == code_commune]
        insufficient = True
        level_label = "10 km — toutes surfaces"
        notes.append("Données insuffisantes : très peu de ventes comparables. Fourchette élargie.")
        if not selected:
            raise NoDataError("Aucune vente de référence de ce type de bien dans un rayon de 10 km.")

    comps, weights, se_median = _prepared(selected)
    base_pm2 = weighted_median([c["pm2_adj"] for c in comps], weights)
    if tight_used:
        notes.append(f"Ventes de surface très proche (±{TIGHT_TOL * 100:.0f} %) retenues pour limiter la dispersion.")
    other_communes = sorted({c["code_commune"] for c in comps if c["code_commune"] != code_commune})
    if other_communes and populations:
        pops = sorted(p["population"] for p in (populations.get(k) for k in other_communes) if p)
        if pops:
            notes.append(f"{len(other_communes)} autre{'s' if len(other_communes) > 1 else ''} commune{'s' if len(other_communes) > 1 else ''} "
                         f"dans les ventes retenues ({pops[0]:,} à {pops[-1]:,} hab.).".replace(",", "\u202f"))

    adjustments: list[Adjustment] = []
    value_base = base_pm2 * surface

    cond_pct, cond_label = CONDITION_ADJ.get(condition, (0.0, "État correct"))
    if condition == "neuf_renove" and year_built and datetime.now(timezone.utc).year - year_built > NEW_BUILD_MAX_AGE:
        cond_pct, cond_label = RENOVATED_OLD_PCT, "Rénové (bâti d'époque)"
    adjustments.append(Adjustment(key="condition", label=cond_label, pct=cond_pct, amount=value_base * cond_pct))

    cost_floor_active = False
    year_adj = year_adjustment(ptype, year_built, bool(getattr(features, "dpe", None)))
    if year_adj:
        age = datetime.now(timezone.utc).year - (year_built or 0)
        if ptype == "maison" and 0 <= age <= NEW_BUILD_MAX_AGE:
            floor_pm2 = NEW_BUILD_FLOOR_PM2 * (1 - NEW_BUILD_DEPRECIATION * age)
            implied = floor_pm2 / base_pm2 - 1
            if implied > year_adj.pct:
                cost_floor_active = True
                year_adj.pct = round(min(implied, NEW_BUILD_MAX_PCT), 4)
                year_adj.label = f"Construction récente ({year_built}) : valeur adossée au coût de construction actuel (≈{floor_pm2:,.0f} €/m²)".replace(",", "\u202f")
                notes.append("Maison récente dans un secteur où les ventes portent surtout sur du bâti ancien : la prime « récent » est relevée "
                             f"jusqu'au coût de construction actuel amorti (≈{floor_pm2:,.0f} €/m² terrain courant compris), plutôt que de "
                             "l'aligner sur des maisons des années 1960–1980.".replace(",", "\u202f"))
        year_adj.amount = value_base * year_adj.pct
        adjustments.append(year_adj)

    adjustments.extend(feature_adjustments(ptype, features, value_base, surface))

    # Le plafond ne s'applique pas quand la valeur est adossée au coût de construction : ce plancher correspond à une maison
    # neuve standard, l'état neuf et les équipements (PAC, DPE A…) s'y ajoutent réellement.
    declared = [a for a in adjustments if a.key != "year"]
    total = sum(a.pct for a in declared)
    cap = DECLARED_MAX_UP if total > 0 else DECLARED_MAX_DOWN
    if abs(total) > abs(cap) and not (cost_floor_active and total > 0):
        scale = abs(cap) / abs(total)
        for a in declared:
            a.pct, a.amount = round(a.pct * scale, 4), value_base * a.pct * scale
        notes.append(f"État et équipements déclarés plafonnés à {cap * 100:+.0f} % au total : la vente type du secteur est déjà une maison "
                     "habitable et équipée, l'écart avec elle reste donc borné.")

    land_amount = 0.0
    if ptype == "maison" and land_surface is not None:
        comp_land = [c.get("land_surface") or 0.0 for c in comps]
        med_land = median(comp_land) if comp_land else 0.0
        excess = land_surface - med_land
        if excess > LAND_FULL_PRICE_M2:  # dégressif : au-delà de +500 m², le m² supplémentaire vaut 3 € et non 12 €
            raw = LAND_FULL_PRICE_M2 * LAND_PRICE_PER_M2 + (excess - LAND_FULL_PRICE_M2) * LAND_EXTRA_PRICE_PER_M2
        else:
            raw = excess * LAND_PRICE_PER_M2
        land_amount = clamp(raw, -LAND_CAP_DOWN * value_base, LAND_CAP_UP * value_base)
        adjustments.append(Adjustment(
            key="land", label=f"Terrain {int(land_surface)} m² vs {int(med_land)} m² (médiane des comparables)",
            pct=land_amount / value_base if value_base else 0.0, amount=land_amount))

    pct_total = sum(a.pct for a in adjustments if a.key != "land")
    value = value_base * (1 + pct_total) + land_amount

    # Dispersion and confidence (on size-adjusted prices/m²)
    rel_iqr = _rel_iqr(comps)
    med_age = median([c["age_years"] for c in comps])
    n = len(comps)

    n_score = min(n, 20) / 20 * 40
    disp_score = 30 * clamp(1 - (rel_iqr - 0.15) / 0.45, 0, 1)
    rec_score = 20 * clamp(1 - (med_age - 1) / 3, 0, 1)
    w_dist_med = weighted_median([c["distance_m"] for c in comps], weights) if comps else 0.0
    prox_score = 10 if w_dist_med <= 500 else 8 if w_dist_med <= 1500 else 6 if w_dist_med <= 3000 else 4 if w_dist_med <= 5000 else 2
    score = int(round(n_score + disp_score + rec_score + prox_score))
    if insufficient:
        score = min(score, 35)
    level = "eleve" if score >= 70 else "moyen" if score >= 45 else "faible"

    details = [
        ConfidenceDetail(key="count", label="Nombre de comparables", score=round(n_score, 1), max_score=40,
                         hint=f"{n} ventes retenues (20+ pour le maximum)"),
        ConfidenceDetail(key="dispersion", label="Homogénéité des prix", score=round(disp_score, 1), max_score=30,
                         hint=f"Dispersion des prix/m² (ramenés à {surface:g} m²) : ±{rel_iqr * 50:.0f} %"),
        ConfidenceDetail(key="recency", label="Récence des ventes", score=round(rec_score, 1), max_score=20,
                         hint=f"Âge médian des ventes : {med_age * 12:.0f} mois"),
        ConfidenceDetail(key="proximity", label="Proximité", score=prox_score, max_score=10,
                         hint=f"Périmètre retenu : {level_label} · distance médiane pondérée {w_dist_med / 1000:.1f} km".replace(".", ",")),
    ]

    # Fourchette fixe ±5 % autour de la valeur centrale ; la fiabilité (dispersion, nombre de ventes) est exposée à part.
    half = RANGE_HALF
    if insufficient:
        notes.append("Peu de ventes comparables : la fourchette de ±5 % doit être lue avec prudence.")

    if med_age > 2.5:
        notes.append("Les ventes retenues sont relativement anciennes : le marché a pu évoluer depuis.")

    top = sorted(zip(comps, weights), key=lambda p: p[1], reverse=True)[:30]
    comparables = [Comparable(
        date=c["date"].strftime("%Y-%m-%d"), distance_m=int(c["distance_m"]), surface=c["surface"],
        rooms=c.get("rooms"), price=c["price"], price_m2=round(c["price_m2"]), land_surface=c.get("land_surface"),
        commune=c["commune"], population=c.get("population"), property_type=c["type"], weight=round(w, 4)) for c, w in top]

    value_r = round_to(value, 1000)
    return Estimation(
        method=METHOD_VERSION,
        value=value_r,
        low=round_to(value_r * (1 - half), 1000),
        high=round_to(value_r * (1 + half), 1000),
        price_m2=round_to(value_r / surface, 10),
        base_price_m2=round_to(base_pm2, 10),
        confidence=Confidence(score=score, level=level, n_comparables=n,
                              dispersion_pct=round(rel_iqr * 50, 1), median_age_months=int(round(med_age * 12)),
                              radius_label=level_label, details=details),
        insufficient_data=insufficient,
        notes=notes,
        adjustments=adjustments,
        market=_market(cands, code_commune),
        comparables=comparables,
    )


async def estimate(db, *, lat: float, lon: float, code_commune: str, ptype: str, surface: float,
                   condition: str, year_built: Optional[int], land_surface: Optional[float],
                   exclude_mutation_id: Optional[str] = None, features=None) -> Estimation:
    cands = await fetch_candidates(db, lat, lon, code_commune, ptype, exclude_mutation_id)
    if not cands:
        raise NoDataError("Aucune vente de référence de ce type de bien dans la zone couverte (rayon 10 km).")
    populations = await communes.load_populations(db)
    return estimate_from_candidates(cands, surface=surface, ptype=ptype, condition=condition,
                                    year_built=year_built, land_surface=land_surface, code_commune=code_commune,
                                    features=features, populations=populations)


async def run_validation(db, n: int = 40) -> dict:
    """Back-test: estimate real recent DVF sales (excluded from their own comparables)."""
    since = datetime.now(timezone.utc) - timedelta(days=540)
    sample = await db.dvf_sales.aggregate([
        {"$match": {"date": {"$gte": since}}},
        {"$sample": {"size": n}},
    ]).to_list(n)
    results = []
    for s in sample:
        lon, lat = s["location"]["coordinates"]
        try:
            est = await estimate(db, lat=lat, lon=lon, code_commune=s["code_commune"], ptype=s["type"],
                                 surface=s["surface"], condition="correct", year_built=None,
                                 land_surface=s.get("land_surface") if s["type"] == "maison" else None,
                                 exclude_mutation_id=s["mutation_id"])
        except NoDataError:
            continue
        ape = abs(est.value - s["price"]) / s["price"]
        results.append({
            "commune": s["commune"], "type": s["type"], "surface": s["surface"], "actual": s["price"],
            "estimated": est.value, "low": est.low, "high": est.high, "ape": round(ape, 4),
            "in_range": est.low <= s["price"] <= est.high, "confidence": est.confidence.level,
            "score": est.confidence.score,
        })
    if not results:
        return {"n": 0, "results": []}

    def agg(rows: list[dict]) -> dict:
        apes = [r["ape"] for r in rows]
        return {
            "n": len(rows),
            "mape": round(sum(apes) / len(apes) * 100, 1),
            "median_ape": round(median(apes) * 100, 1),
            "coverage": round(sum(1 for r in rows if r["in_range"]) / len(rows) * 100, 1),
            "within_15pct": round(sum(1 for a in apes if a <= 0.15) / len(apes) * 100, 1),
        }

    by_level = {lvl: agg([r for r in results if r["confidence"] == lvl])
                for lvl in ("eleve", "moyen", "faible") if any(r["confidence"] == lvl for r in results)}
    by_type = {t: agg([r for r in results if r["type"] == t])
               for t in ("appartement", "maison") if any(r["type"] == t for r in results)}
    return {**agg(results), "by_confidence": by_level, "by_type": by_type,
            "results": sorted(results, key=lambda r: r["ape"])}
