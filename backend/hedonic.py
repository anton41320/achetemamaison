"""Phase 2 — interpretable hedonic model.

log(price) = a + b1·log(surface) + b2·rooms + b3·log1p(land)·maison + b4·maison
             + b5·(sale_year - REF_YEAR) + effect(commune)

Commune effects are estimated as fixed effects (within transformation) and
shrunk toward the department effect for small communes. Everything is stored in
MongoDB (`models` collection) so predictions are deterministic and explainable.
The model is compared to the comparables baseline, never used to replace it.
"""
from __future__ import annotations

import logging
import math
import threading
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from pymongo import MongoClient

from models import HedonicFactor, HedonicResult

logger = logging.getLogger("hedonic")

MODEL_NAME = "hedonic_v1"
REF_YEAR = 2025          # market level at which values are expressed
MIN_COMMUNE_SALES = 20
SHRINK_K = 15.0
FEATURES = ["log_surface", "rooms", "log_land_maison", "maison", "year_rel"]

_lock = threading.Lock()
_training = False
_cache: dict = {}


def is_training() -> bool:
    return _training


def _features(surface: float, rooms: Optional[int], land: Optional[float], ptype: str, year: int) -> np.ndarray:
    maison = 1.0 if ptype == "maison" else 0.0
    r = float(min(max(rooms or 3, 1), 8))
    land_v = math.log1p(min(max(land or 0.0, 0.0), 20000)) * maison
    return np.array([math.log(surface), r, land_v, maison, float(year - REF_YEAR)])


def _load_rows(db) -> tuple[np.ndarray, np.ndarray, list[str], list[str], list[int]]:
    cur = db.dvf_sales.find({}, {"price": 1, "surface": 1, "rooms": 1, "land_surface": 1, "type": 1,
                                 "code_commune": 1, "dept": 1, "year": 1, "date": 1})
    X, y, communes, depts, years = [], [], [], [], []
    for d in cur:
        X.append(_features(d["surface"], d.get("rooms"), d.get("land_surface"), d["type"], d["year"]))
        y.append(math.log(d["price"]))
        communes.append(d["code_commune"])
        depts.append(d["dept"])
        years.append(d["year"])
    return np.array(X), np.array(y), communes, depts, years


def _fit(X: np.ndarray, y: np.ndarray, communes: list[str], depts: list[str]) -> dict:
    n = len(y)
    comm = np.array(communes)
    dep = np.array(depts)
    # Group = commune if large enough, otherwise its department bucket.
    uniq, counts = np.unique(comm, return_counts=True)
    big = set(uniq[counts >= MIN_COMMUNE_SALES].tolist())
    groups = np.array([c if c in big else f"dept_{d}" for c, d in zip(comm, dep)])
    g_uniq, g_idx = np.unique(groups, return_inverse=True)

    # Within transformation (demean by group) → OLS on continuous features.
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
    # Department effects (relative to intercept)
    dept_eff: dict[str, float] = {}
    for d in np.unique(dep):
        dept_eff[str(d)] = float(resid[dep == d].mean() - intercept)
    # Commune effects shrunk toward their department effect
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


def _evaluate(model: dict, X, y, communes, depts) -> dict:
    preds = np.array([_predict_log(model, X[i], communes[i], depts[i]) for i in range(len(y))])
    ape = np.abs(np.exp(preds) - np.exp(y)) / np.exp(y)
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {"n": int(len(y)), "mape": round(float(ape.mean() * 100), 1),
            "median_ape": round(float(np.median(ape) * 100), 1),
            "within_15pct": round(float((ape <= 0.15).mean() * 100), 1),
            "r2_log": round(1 - ss_res / ss_tot, 3) if ss_tot else None}


def train(mongo_url: str, db_name: str) -> None:
    global _training
    with _lock:
        if _training:
            return
        _training = True
    client = MongoClient(mongo_url)
    db = client[db_name]
    try:
        X, y, communes, depts, years = _load_rows(db)
        if len(y) < 500:
            logger.warning("Not enough DVF rows to train hedonic model (%d)", len(y))
            return
        yrs = np.array(years)
        test_year = int(yrs.max())
        tr = yrs < test_year
        te = ~tr
        holdout_metrics = None
        if te.sum() >= 200 and tr.sum() >= 500:
            m_tr = _fit(X[tr], y[tr], [c for c, k in zip(communes, tr) if k], [d for d, k in zip(depts, tr) if k])
            holdout_metrics = _evaluate(m_tr, X[te], y[te], [c for c, k in zip(communes, te) if k],
                                        [d for d, k in zip(depts, te) if k])
            holdout_metrics["test_year"] = test_year
        model = _fit(X, y, communes, depts)
        model["in_sample"] = _evaluate(model, X, y, communes, depts)
        model["holdout"] = holdout_metrics
        # Reference (typical) property per type: medians used for factor decomposition
        refs = {}
        for t, flag in (("appartement", 0.0), ("maison", 1.0)):
            mask = X[:, 3] == flag
            if mask.sum() == 0:
                continue
            refs[t] = {"surface": float(np.exp(np.median(X[mask, 0]))), "rooms": float(np.median(X[mask, 1])),
                       "land": float(np.expm1(np.median(X[mask, 2]))) if flag else 0.0}
        model["refs"] = refs
        model["name"] = MODEL_NAME
        model["features"] = FEATURES
        model["ref_year"] = REF_YEAR
        model["trained_at"] = datetime.now(timezone.utc)
        db.models.replace_one({"_id": MODEL_NAME}, {"_id": MODEL_NAME, **model}, upsert=True)
        _cache.clear()
        _cache.update(model)
        logger.info("Hedonic model trained on %d sales: %s | holdout %s", model["n"], model["in_sample"], holdout_metrics)
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
        "in_sample": model.get("in_sample"), "holdout": model.get("holdout"), "sigma": round(model["sigma"], 4),
        "communes_with_effect": len(model["commune_effects"]), "ref_year": model["ref_year"],
    }


def explain(model: dict, *, surface: float, rooms: int, land: Optional[float], ptype: str, code_commune: str,
            commune: str, dept: str, condition_pct: float, condition_label: str, year_pct: float,
            year_label: Optional[str], comparables_value: float) -> HedonicResult:
    beta = np.array(model["beta"])
    x = _features(surface, rooms, land, ptype, REF_YEAR)
    ref = model["refs"].get(ptype) or {"surface": surface, "rooms": rooms, "land": land or 0}
    x_ref = _features(ref["surface"], int(round(ref["rooms"])), ref["land"], ptype, REF_YEAR)
    dept_eff = model["dept_effects"].get(dept, 0.0)
    comm_eff = model["commune_effects"].get(code_commune)
    loc_eff = (comm_eff if comm_eff is not None else dept_eff) - dept_eff

    log_ref = model["intercept"] + float(np.dot(beta, x_ref)) + dept_eff
    contrib = beta * (x - x_ref)

    factors: list[HedonicFactor] = []

    def add(key: str, label: str, log_c: float, detail: str, learned: bool = True):
        factors.append(HedonicFactor(key=key, label=label, pct=round(math.exp(log_c) - 1, 4), detail=detail, learned=learned))

    add("location", f"Localisation : {commune}", loc_eff,
        (f"Effet commune estimé sur {model['commune_counts'].get(code_commune, 0)} ventes, "
         f"vs moyenne du département {dept}") if comm_eff is not None
        else f"Commune peu vendue : effet du département {dept} appliqué")
    add("surface", f"Surface {surface:.0f} m²", float(contrib[0]),
        f"vs {ref['surface']:.0f} m² pour un(e) {ptype} type ; élasticité {beta[0]:.2f}")
    add("rooms", f"{rooms} pièces", float(contrib[1]), f"vs {ref['rooms']:.0f} pièces en médiane")
    if ptype == "maison":
        add("land", f"Terrain {int(land or 0)} m²", float(contrib[2]), f"vs {ref['land']:.0f} m² en médiane")
    add("condition", condition_label, math.log1p(condition_pct), "Ajustement déclaré (non présent dans DVF)", learned=False)
    if year_label:
        add("year", year_label, math.log1p(year_pct), "Ajustement déclaré (non présent dans DVF)", learned=False)

    log_pred = log_ref + float(np.sum(contrib)) + loc_eff
    value = math.exp(log_pred) * (1 + condition_pct) * (1 + year_pct)
    holdout = model.get("holdout") or model.get("in_sample") or {}
    # Robust interval: typical (median) error of the model on held-out sales
    half = (holdout.get("median_ape") or 20.0) / 100.0
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
