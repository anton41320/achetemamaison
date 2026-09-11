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

from models import (Adjustment, Comparable, Confidence, ConfidenceDetail, Estimation,
                    MarketLevel)

MIN_COMPS = 8
MIN_VIABLE = 3
LOOKBACK_YEARS = 5
MARKET_YEARS = 3
TIGHT_TOL = 0.15  # surface tolerance tried first at each radius (less price/m² dispersion)
IRREDUCIBLE = 0.07  # unobserved specifics of the property after declared adjustments
SIZE_ELASTICITY = 0.20  # price/m² ∝ surface^-0.20 (hedonic log-surface coefficient ≈ 0.80)
MAX_HALF = 0.15  # widest range shown when data is viable; the confidence score carries the residual risk
METHOD_VERSION = "comparables_dvf_v2"  # bump when the range/selection logic changes: stored estimations auto-refresh

LEVELS = [
    ("À 500 m", 500, 0.30),
    ("Quartier (1,5 km)", 1500, 0.30),
    ("Commune", None, 0.35),
    ("Secteur (5 km)", 5000, 0.35),
]

CONDITION_ADJ = {
    "a_renover": (-0.12, "À rénover"),
    "travaux": (-0.06, "Travaux à prévoir"),
    "correct": (0.0, "État correct"),
    "bon": (0.04, "Bon état"),
    "neuf_renove": (0.10, "Neuf / rénové"),
}

LAND_PRICE_PER_M2 = 12.0

# Declared feature adjustments (transparent, bounded). DVF has none of these, so they are
# applied as explicit multiplicative corrections and listed one by one.
FEATURE_MAX_TOTAL = 0.25


def feature_adjustments(ptype: str, f, value_base: float) -> list[Adjustment]:
    out: list[tuple[str, str, float]] = []
    if f is None:
        return []
    maison = ptype == "maison"
    if f.pool == "hors_sol":
        out.append(("feat_pool", "Piscine hors-sol", 0.01))
    elif f.pool == "enterree":
        out.append(("feat_pool", "Piscine enterrée", 0.06))
    if maison and f.fenced:
        out.append(("feat_fenced", "Terrain clos", 0.015))
    if maison and f.motorized_gate:
        out.append(("feat_gate", "Portail motorisé", 0.01))
    if f.terrace:
        out.append(("feat_terrace", "Terrasse", 0.015))
    if f.garage == "un":
        out.append(("feat_garage", "Garage", 0.03))
    elif f.garage == "deux_plus":
        out.append(("feat_garage", "Double garage ou plus", 0.05))
    if maison and f.outbuilding:
        out.append(("feat_outbuilding", "Dépendance / abri", 0.02))
    if f.orientation in ("sud", "sud_ouest", "sud_est"):
        out.append(("feat_orientation", "Exposition sud", 0.02))
    elif f.orientation == "nord":
        out.append(("feat_orientation", "Exposition nord", -0.02))
    if maison and f.single_storey:
        out.append(("feat_single_storey", "Plain-pied", 0.03))
    if maison and f.basement:
        out.append(("feat_basement", "Sous-sol / cave", 0.015))
    if maison and f.convertible_attic:
        out.append(("feat_attic", "Combles aménageables", 0.02))
    if f.bathrooms is not None and f.bathrooms >= 2:
        out.append(("feat_bathrooms", f"{f.bathrooms} salles de bain", 0.015))
    heating = {"pompe_a_chaleur": ("Pompe à chaleur", 0.03), "electrique": ("Chauffage électrique", -0.02),
               "fioul": ("Chauffage au fioul", -0.04)}
    if f.heating in heating:
        label, pct = heating[f.heating]
        out.append(("feat_heating", label, pct))
    dpe = {"A": 0.06, "B": 0.06, "C": 0.03, "D": 0.0, "E": -0.04, "F": -0.09, "G": -0.14}
    if f.dpe in dpe and dpe[f.dpe] != 0:
        out.append(("feat_dpe", f"DPE {f.dpe}", dpe[f.dpe]))
    if f.double_glazing:
        out.append(("feat_glazing", "Double vitrage", 0.01))
    if f.air_conditioning:
        out.append(("feat_ac", "Climatisation", 0.015))
    if f.solar_panels:
        out.append(("feat_solar", "Panneaux solaires", 0.02))
    if not maison:
        if f.floor is not None:
            if f.floor == 0:
                out.append(("feat_floor", "Rez-de-chaussée", -0.03))
            elif f.floor >= 3 and f.elevator is False:
                out.append(("feat_floor", f"{f.floor}e étage sans ascenseur", -0.04))
            elif f.floor >= 2 and f.elevator:
                out.append(("feat_floor", f"{f.floor}e étage avec ascenseur", 0.02))
        if f.balcony:
            out.append(("feat_balcony", "Balcon / terrasse", 0.03))
        if f.parking:
            out.append(("feat_parking", "Parking / box", 0.04))
        if f.cellar:
            out.append(("feat_cellar", "Cave", 0.01))
    total = sum(p for _, _, p in out)
    scale = min(1.0, FEATURE_MAX_TOTAL / abs(total)) if abs(total) > FEATURE_MAX_TOTAL else 1.0
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
        "$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": 5000}}}
    near = await db.dvf_sales.find(near_q, proj).to_list(3000)
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


def _in_scope(c: dict, radius: Optional[int], code_commune: str) -> bool:
    if radius is None:
        return c["code_commune"] == code_commune
    return c["distance_m"] <= radius


def _weight(c: dict, surface: float) -> float:
    w_time = 0.5 ** (c["age_years"] / 2.0)
    w_dist = 1.0 / (1.0 + c["distance_m"] / 500.0)
    w_surf = math.exp(-((math.log(c["surface"] / surface)) / 0.25) ** 2)
    return w_time * w_dist * max(w_surf, 0.05)


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
    for label, radius, _ in LEVELS[:3]:
        sel = [c["price_m2"] for c in recent if _in_scope(c, radius, code_commune)]
        out.append(MarketLevel(label=label, radius_m=radius, count=len(sel),
                               median_pm2=round_to(median(sel), 10) if sel else None))
    return out


def estimate_from_candidates(cands: list[dict], *, surface: float, ptype: str, condition: str,
                             year_built: Optional[int], land_surface: Optional[float],
                             code_commune: str, features=None) -> Estimation:
    notes: list[str] = []
    selected: list[dict] = []
    level_label = LEVELS[-1][0]
    tight_used = False

    # Size-adjusted price/m²: every sale is brought to the target surface (price/m² falls with size).
    for c in cands:
        ratio = clamp(c["surface"] / surface, 0.5, 2.0)
        c["pm2_adj"] = c["price_m2"] * ratio ** SIZE_ELASTICITY

    def _prepared(sel: list[dict]) -> tuple[list[dict], list[float], float]:
        comps_ = _trim_outliers(sel)
        w_ = [_weight(c, surface) for c in comps_]
        return comps_, w_, _se_median(comps_, w_)

    for idx, (label, radius, tol) in enumerate(LEVELS):
        in_scope = [c for c in cands if _in_scope(c, radius, code_commune)]
        tight = [c for c in in_scope if (1 - TIGHT_TOL) * surface <= c["surface"] <= (1 + TIGHT_TOL) * surface]
        wide = [c for c in in_scope if (1 - tol) * surface <= c["surface"] <= (1 + tol) * surface]
        sel = wide
        if len(tight) >= MIN_COMPS and len(wide) >= MIN_COMPS:
            # Keep whichever set pins the central value best (fewer but closer sales vs more but noisier).
            if _prepared(tight)[2] < _prepared(wide)[2]:
                sel = tight
        if len(sel) >= MIN_COMPS or idx == len(LEVELS) - 1:
            selected, level_label = sel, label
            tight_used = sel is tight
            if idx > 0 and len(sel) >= MIN_COMPS:
                notes.append(f"Peu de ventes comparables à 500 m : rayon élargi ({label.lower()}).")
            break

    insufficient = False
    if len(selected) < MIN_VIABLE:
        # Drop the surface filter: use every sale of this type in the sector / commune.
        selected = [c for c in cands if _in_scope(c, 5000, code_commune) or c["code_commune"] == code_commune]
        insufficient = True
        level_label = "Secteur (5 km) — toutes surfaces"
        notes.append("Données insuffisantes : très peu de ventes comparables. Fourchette élargie.")
        if not selected:
            raise NoDataError("Aucune vente DVF de ce type de bien dans un rayon de 5 km.")

    comps, weights, se_median = _prepared(selected)
    base_pm2 = weighted_median([c["pm2_adj"] for c in comps], weights)
    if tight_used:
        notes.append(f"Ventes de surface très proche (±{TIGHT_TOL * 100:.0f} %) retenues pour limiter la dispersion.")

    adjustments: list[Adjustment] = []
    value_base = base_pm2 * surface

    cond_pct, cond_label = CONDITION_ADJ.get(condition, (0.0, "État correct"))
    adjustments.append(Adjustment(key="condition", label=cond_label, pct=cond_pct, amount=value_base * cond_pct))

    if year_built:
        if year_built < 1950:
            y_pct, y_label = -0.03, "Construction ancienne (avant 1950)"
        elif year_built < 1980:
            y_pct, y_label = -0.04, "Construction 1950–1979 (performance énergétique)"
        elif year_built < 2005:
            y_pct, y_label = 0.0, "Construction 1980–2004"
        else:
            y_pct, y_label = 0.05, "Construction récente (2005+)"
        adjustments.append(Adjustment(key="year", label=y_label, pct=y_pct, amount=value_base * y_pct))

    adjustments.extend(feature_adjustments(ptype, features, value_base))

    land_amount = 0.0
    if ptype == "maison" and land_surface is not None:
        comp_land = [c.get("land_surface") or 0.0 for c in comps]
        med_land = median(comp_land) if comp_land else 0.0
        excess = land_surface - med_land
        land_amount = clamp(excess * LAND_PRICE_PER_M2, -0.10 * value_base, 0.10 * value_base)
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
    prox_map = {LEVELS[0][0]: 10, LEVELS[1][0]: 7, LEVELS[2][0]: 4}
    prox_score = prox_map.get(level_label, 2)
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
                         hint=f"Périmètre retenu : {level_label}"),
    ]

    # Range half-width = uncertainty on the *central value*, not the spread of individual sales.
    # Sampling error of the weighted median combined with an irreducible floor for unobserved specifics,
    # widened when confidence is low or sales are old, and capped so the range stays actionable.
    half = math.sqrt(se_median ** 2 + IRREDUCIBLE ** 2)
    if med_age > 2.0:
        half += 0.02
    half *= 1 + (100 - score) / 400
    half = clamp(half, 0.07, MAX_HALF if score >= 45 else MAX_HALF + 0.05)
    if insufficient:
        half = max(half, 0.25)

    if med_age > 2.5:
        notes.append("Les ventes retenues sont relativement anciennes : le marché a pu évoluer depuis.")

    top = sorted(zip(comps, weights), key=lambda p: p[1], reverse=True)[:30]
    comparables = [Comparable(
        date=c["date"].strftime("%Y-%m-%d"), distance_m=int(c["distance_m"]), surface=c["surface"],
        rooms=c.get("rooms"), price=c["price"], price_m2=round(c["price_m2"]), land_surface=c.get("land_surface"),
        commune=c["commune"], property_type=c["type"], weight=round(w, 4)) for c, w in top]

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
        raise NoDataError("Aucune vente DVF de ce type de bien dans la zone couverte (rayon 5 km).")
    return estimate_from_candidates(cands, surface=surface, ptype=ptype, condition=condition,
                                    year_built=year_built, land_surface=land_surface, code_commune=code_commune,
                                    features=features)


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
