"""Phase 2 — interpretable hedonic model (v2).

log(price) = a + b·features(type-specific surface / rooms elasticities, land, market year)
             + effect(commune, shrunk toward department)
             + micro-location: weighted mean residual of neighbouring sales (same type, 1,5 km, shrunk)

Commune effects are fixed effects (within transformation). The micro-location term is computed at
prediction time from the residuals of nearby DVF sales, so the hedonic value captures the same local
signal as the comparables while staying fully decomposable. Everything is stored in MongoDB (`models`).
"""
from __future__ import annotations

import logging
import math
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from pymongo import MongoClient
from sklearn.neighbors import BallTree

from models import HedonicFactor, HedonicResult

logger = logging.getLogger("hedonic")

MODEL_NAME = "hedonic_v2"
REF_YEAR = 2025          # market level at which values are expressed
MIN_COMMUNE_SALES = 20
SHRINK_K = 15.0
FEATURES = ["log_surface", "log_surface_maison", "rooms", "rooms_maison", "log_land_maison", "maison", "year_rel"]
LOCAL_RADIUS_M = 1500
LOCAL_RADIUS_WIDE_M = 3000
LOCAL_YEARS = 3
LOCAL_K = 60
LOCAL_SHRINK = 8.0
LOCAL_MAX = 0.25
EARTH_M = 6371000.0

_lock = threading.Lock()
_training = False
_cache: dict = {}


def is_training() -> bool:
    return _training


def _features(surface: float, rooms: Optional[int], land: Optional[float], ptype: str, year: int) -> np.ndarray:
    maison = 1.0 if ptype == "maison" else 0.0
    r = float(min(max(rooms or 3, 1), 8))
    ls = math.log(surface)
    land_v = math.log1p(min(max(land or 0.0, 0.0), 20000)) * maison
    return np.array([ls, ls * maison, r, r * maison, land_v, maison, float(year - REF_YEAR)])


def _load_rows(db):
    cur = db.dvf_sales.find({}, {"price": 1, "surface": 1, "rooms": 1, "land_surface": 1, "type": 1,
                                 "code_commune": 1, "dept": 1, "year": 1, "date": 1, "location": 1})
    X, y, communes, depts, years, coords, ages = [], [], [], [], [], [], []
    now = datetime.now(timezone.utc)
    for d in cur:
        X.append(_features(d["surface"], d.get("rooms"), d.get("land_surface"), d["type"], d["year"]))
        y.append(math.log(d["price"]))
        communes.append(d["code_commune"])
        depts.append(d["dept"])
        years.append(d["year"])
        lon, lat = d["location"]["coordinates"]
        coords.append((math.radians(lat), math.radians(lon)))
        dt = d["date"] if d["date"].tzinfo else d["date"].replace(tzinfo=timezone.utc)
        ages.append((now - dt).days / 365.25)
    return np.array(X), np.array(y), communes, depts, years, np.array(coords), np.array(ages)


def _fit(X: np.ndarray, y: np.ndarray, communes: list[str], depts: list[str]) -> dict:
    n = len(y)
    comm = np.array(communes)
    dep = np.array(depts)
    uniq, counts = np.unique(comm, return_counts=True)
    big = set(uniq[counts >= MIN_COMMUNE_SALES].tolist())
    groups = np.array([c if c in big else f"dept_{d}" for c, d in zip(comm, dep)])
    g_uniq, g_idx = np.unique(groups, return_inverse=True)

    Xd = X.copy()
    yd = y.copy()
    for j in range(X.shape[1]):
        means = np.bincount(g_idx, weights=X[:, j]) / np.bincount(g_idx)
        Xd[:, j] -= means[g_idx]
    ymeans = np.bincount(g_idx, weights=y) / np.bincount(g_idx)
    yd -= ymeans[g_idx]
    beta, *_ = np.linalg.lstsq(Xd, yd, rcond=None)

    resid = y - X @ beta
    intercept = float(resid.mean())
    dept_eff: dict[str, float] = {}
    for d in np.unique(dep):
        dept_eff[str(d)] = float(resid[dep == d].mean() - intercept)
    comm_eff: dict[str, float] = {}
    comm_n: dict[str, int] = {}
    for c in big:
        mask = comm == c
        cnt = int(mask.sum())
        d = str(dep[mask][0])
        raw = float(resid[mask].mean() - intercept)
        w = cnt / (cnt + SHRINK_K)
        comm_eff[c] = w * raw + (1 - w) * dept_eff[d]
        comm_n[c] = cnt
    sigma = float(np.std(resid - intercept))
    return {"beta": beta.tolist(), "intercept": intercept, "dept_effects": dept_eff,
            "commune_effects": comm_eff, "commune_counts": comm_n, "sigma": sigma, "n": n}


def _predict_log(model: dict, x: np.ndarray, code_commune: str, dept: str) -> float:
    eff = model["commune_effects"].get(code_commune, model["dept_effects"].get(dept, 0.0))
    return model["intercept"] + float(np.dot(model["beta"], x)) + eff


def _local_adjustment(resids: np.ndarray, dists_m: np.ndarray, ages: np.ndarray) -> tuple[float, float]:
    """Weighted mean residual of neighbours (distance & recency), shrunk toward 0 by effective count."""
    if len(resids) == 0:
        return 0.0, 0.0
    w = (1.0 / (1.0 + dists_m / 500.0)) * (0.5 ** (ages / 2.0))
    n_eff = float(w.sum() ** 2 / (w ** 2).sum()) if w.sum() > 0 else 0.0
    adj = float(np.sum(w * resids) / w.sum()) * n_eff / (n_eff + LOCAL_SHRINK)
    return max(-LOCAL_MAX, min(LOCAL_MAX, adj)), n_eff


def _evaluate(model: dict, X, y, communes, depts, local: Optional[np.ndarray] = None) -> dict:
    preds = np.array([_predict_log(model, X[i], communes[i], depts[i]) for i in range(len(y))])
    if local is not None:
        preds = preds + local
    ape = np.abs(np.exp(preds) - np.exp(y)) / np.exp(y)
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {"n": int(len(y)), "mape": round(float(ape.mean() * 100), 1),
            "median_ape": round(float(np.median(ape) * 100), 1),
            "within_15pct": round(float((ape <= 0.15).mean() * 100), 1),
            "r2_log": round(1 - ss_res / ss_tot, 3) if ss_tot else None}


def _holdout_local(model: dict, X_tr, y_tr, comm_tr, dep_tr, coords_tr, ages_tr, X_te, coords_te, types_tr, types_te) -> np.ndarray:
    """Micro-location term for each test sale from *training* neighbours only (honest evaluation)."""
    resid_tr = y_tr - np.array([_predict_log(model, X_tr[i], comm_tr[i], dep_tr[i]) for i in range(len(y_tr))])
    out = np.zeros(len(X_te))
    for t in (0.0, 1.0):
        m_tr = types_tr == t
        m_te = np.where(types_te == t)[0]
        if m_tr.sum() == 0 or len(m_te) == 0:
            continue
        tree = BallTree(coords_tr[m_tr], metric="haversine")
        r_tr, a_tr = resid_tr[m_tr], ages_tr[m_tr]
        idx_all, d_all = tree.query_radius(coords_te[m_te], r=LOCAL_RADIUS_M / EARTH_M, return_distance=True, sort_results=True)
        for j, (idx, d) in enumerate(zip(idx_all, d_all)):
            idx, d = idx[:LOCAL_K], d[:LOCAL_K]
            recent = a_tr[idx] <= LOCAL_YEARS + 1  # neighbours recent relative to the test year
            out[m_te[j]] = _local_adjustment(r_tr[idx][recent], d[recent] * EARTH_M, a_tr[idx][recent])[0]
    return out


def train(mongo_url: str, db_name: str) -> None:
    global _training
    with _lock:
        if _training:
            return
        _training = True
    client = MongoClient(mongo_url)
    db = client[db_name]
    try:
        X, y, communes, depts, years, coords, ages = _load_rows(db)
        if len(y) < 500:
            logger.warning("Not enough DVF rows to train hedonic model (%d)", len(y))
            return
        yrs = np.array(years)
        test_year = int(yrs.max())
        tr = yrs < test_year
        te = ~tr
        holdout_metrics = holdout_local = None
        if te.sum() >= 200 and tr.sum() >= 500:
            comm_tr, dep_tr = [c for c, k in zip(communes, tr) if k], [d for d, k in zip(depts, tr) if k]
            comm_te, dep_te = [c for c, k in zip(communes, te) if k], [d for d, k in zip(depts, te) if k]
            m_tr = _fit(X[tr], y[tr], comm_tr, dep_tr)
            holdout_metrics = _evaluate(m_tr, X[te], y[te], comm_te, dep_te)
            holdout_metrics["test_year"] = test_year
            rng = np.random.default_rng(42)
            sub = rng.choice(np.where(te)[0], size=min(3000, int(te.sum())), replace=False)
            local = _holdout_local(m_tr, X[tr], y[tr], comm_tr, dep_tr, coords[tr], ages[tr], X[sub], coords[sub],
                                   X[tr][:, 5], X[sub][:, 5])
            holdout_local = _evaluate(m_tr, X[sub], y[sub], [communes[i] for i in sub], [depts[i] for i in sub], local)
            holdout_local["test_year"] = test_year
            holdout_local["without_local"] = _evaluate(m_tr, X[sub], y[sub], [communes[i] for i in sub], [depts[i] for i in sub])
        model = _fit(X, y, communes, depts)
        model["in_sample"] = _evaluate(model, X, y, communes, depts)
        model["holdout"] = holdout_metrics
        model["holdout_local"] = holdout_local
        refs = {}
        for t, flag in (("appartement", 0.0), ("maison", 1.0)):
            mask = X[:, 5] == flag
            if mask.sum() == 0:
                continue
            refs[t] = {"surface": float(np.exp(np.median(X[mask, 0]))), "rooms": float(np.median(X[mask, 2])),
                       "land": float(np.expm1(np.median(X[mask, 4]))) if flag else 0.0}
        model["refs"] = refs
        model["name"] = MODEL_NAME
        model["features"] = FEATURES
        model["ref_year"] = REF_YEAR
        model["trained_at"] = datetime.now(timezone.utc)
        db.models.replace_one({"_id": MODEL_NAME}, {"_id": MODEL_NAME, **model}, upsert=True)
        _cache.clear()
        _cache.update(model)
        logger.info("Hedonic model trained on %d sales: %s | holdout %s | holdout+local %s", model["n"], model["in_sample"],
                    holdout_metrics, holdout_local)
    finally:
        _training = False
        client.close()


async def load_model(db) -> Optional[dict]:
    if _cache:
        return _cache
    doc = await db.models.find_one({"_id": MODEL_NAME})
    if doc:
        _cache.update(doc)
    return doc


def model_summary(model: dict) -> dict:
    return {
        "name": model["name"], "trained_at": model["trained_at"].isoformat() if model.get("trained_at") else None,
        "n": model["n"], "features": model["features"], "coefficients": dict(zip(model["features"], model["beta"])),
        "in_sample": model.get("in_sample"), "holdout": model.get("holdout"), "holdout_local": model.get("holdout_local"),
        "sigma": round(model["sigma"], 4), "communes_with_effect": len(model["commune_effects"]), "ref_year": model["ref_year"],
    }


async def local_effect(db, model: dict, *, lat: float, lon: float, ptype: str) -> dict:
    """Micro-location term from residuals of neighbouring sales of the same type (1,5 km, else 3 km)."""
    since = datetime.now(timezone.utc) - timedelta(days=365 * LOCAL_YEARS)
    proj = {"price": 1, "surface": 1, "rooms": 1, "land_surface": 1, "code_commune": 1, "dept": 1, "year": 1, "date": 1, "location": 1}
    now = datetime.now(timezone.utc)
    for radius in (LOCAL_RADIUS_M, LOCAL_RADIUS_WIDE_M):
        rows = await db.dvf_sales.find({"type": ptype, "date": {"$gte": since}, "location": {"$nearSphere": {
            "$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": radius}}}, proj).to_list(LOCAL_K)
        if len(rows) >= 5 or radius == LOCAL_RADIUS_WIDE_M:
            break
    if not rows:
        return {"adj": 0.0, "n": 0, "radius_m": LOCAL_RADIUS_WIDE_M}
    resids, dists, ages = [], [], []
    p1 = math.radians(lat)
    for r in rows:
        x = _features(r["surface"], r.get("rooms"), r.get("land_surface"), ptype, r["year"])
        resids.append(math.log(r["price"]) - _predict_log(model, x, r["code_commune"], r["dept"]))
        rlon, rlat = r["location"]["coordinates"]
        p2 = math.radians(rlat)
        a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(rlon - lon) / 2) ** 2
        dists.append(2 * EARTH_M * math.asin(math.sqrt(a)))
        dt = r["date"] if r["date"].tzinfo else r["date"].replace(tzinfo=timezone.utc)
        ages.append((now - dt).days / 365.25)
    adj, _ = _local_adjustment(np.array(resids), np.array(dists), np.array(ages))
    return {"adj": adj, "n": len(rows), "radius_m": radius}


def explain(model: dict, *, surface: float, rooms: int, land: Optional[float], ptype: str, code_commune: str,
            commune: str, dept: str, condition_pct: float, condition_label: str, year_pct: float,
            year_label: Optional[str], comparables_value: float, features_pct: float = 0.0,
            local: Optional[dict] = None) -> HedonicResult:
    beta = np.array(model["beta"])
    x = _features(surface, rooms, land, ptype, REF_YEAR)
    ref = model["refs"].get(ptype) or {"surface": surface, "rooms": rooms, "land": land or 0}
    x_ref = _features(ref["surface"], int(round(ref["rooms"])), ref["land"], ptype, REF_YEAR)
    dept_eff = model["dept_effects"].get(dept, 0.0)
    comm_eff = model["commune_effects"].get(code_commune)
    loc_eff = (comm_eff if comm_eff is not None else dept_eff) - dept_eff
    local_adj = float((local or {}).get("adj", 0.0))

    log_ref = model["intercept"] + float(np.dot(beta, x_ref)) + dept_eff
    contrib = beta * (x - x_ref)
    maison = ptype == "maison"
    elasticity = beta[0] + (beta[1] if maison else 0.0)

    factors: list[HedonicFactor] = []

    def add(key: str, label: str, log_c: float, detail: str, learned: bool = True):
        factors.append(HedonicFactor(key=key, label=label, pct=round(math.exp(log_c) - 1, 4), detail=detail, learned=learned))

    add("location", f"Localisation : {commune}", loc_eff,
        (f"Effet commune estimé sur {model['commune_counts'].get(code_commune, 0)} ventes, "
         f"vs moyenne du département {dept}") if comm_eff is not None
        else f"Commune peu vendue : effet du département {dept} appliqué")
    if local and local.get("n", 0) > 0:
        add("micro_location", "Micro-localisation (ventes voisines)", local_adj,
            f"Écart des {local['n']} ventes de {ptype}s dans un rayon de {local['radius_m'] / 1000:g} km par rapport au modèle, "
            f"pondéré par distance et récence".replace(".", ","))
    add("surface", f"Surface {surface:.0f} m²", float(contrib[0] + contrib[1]),
        f"vs {ref['surface']:.0f} m² pour un(e) {ptype} type ; élasticité {elasticity:.2f}")
    add("rooms", f"{rooms} pièces", float(contrib[2] + contrib[3]), f"vs {ref['rooms']:.0f} pièces en médiane")
    if maison:
        add("land", f"Terrain {int(land or 0)} m²", float(contrib[4]), f"vs {ref['land']:.0f} m² en médiane")
    add("condition", condition_label, math.log1p(condition_pct), "Ajustement déclaré (non présent dans DVF)", learned=False)
    if year_label:
        add("year", year_label, math.log1p(year_pct), "Ajustement déclaré (non présent dans DVF)", learned=False)
    if abs(features_pct) > 0.0005:
        add("features", "Équipements & confort déclarés", math.log1p(features_pct),
            "Somme des ajustements déclarés (piscine, chauffage, DPE, garage…)", learned=False)

    log_pred = log_ref + float(np.sum(contrib)) + loc_eff + local_adj
    value = math.exp(log_pred) * (1 + condition_pct) * (1 + year_pct) * (1 + features_pct)
    holdout = (model.get("holdout_local") if local else None) or model.get("holdout") or model.get("in_sample") or {}
    half = min((holdout.get("median_ape") or 20.0) / 100.0, 0.15)
    low, high = value * (1 - half), value * (1 + half)
    delta = (value - comparables_value) / comparables_value if comparables_value else 0.0
    agreement = "convergent" if abs(delta) < 0.10 else "ecart_modere" if abs(delta) < 0.25 else "divergent"
    return HedonicResult(
        model_version=MODEL_NAME,
        value=float(int(round(value / 1000)) * 1000),
        low=float(int(round(low / 1000)) * 1000),
        high=float(int(round(high / 1000)) * 1000),
        price_m2=float(int(round(value / surface / 10)) * 10),
        reference_value=float(int(round(math.exp(log_ref) / 1000)) * 1000),
        reference_label=f"{ptype.capitalize()} type du département {dept} ({ref['surface']:.0f} m², {ref['rooms']:.0f} p.)",
        factors=factors,
        delta_vs_comparables_pct=round(delta, 4),
        agreement=agreement,
        model_median_ape=holdout.get("median_ape"),
        model_n=model["n"],
    )
