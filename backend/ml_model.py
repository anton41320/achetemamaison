"""Phase 3 — gradient boosting (LightGBM) with temporal validation, SHAP explanations
and a promotion gate against the comparables baseline.

Train on years < TEST_YEAR, test on TEST_YEAR. The model is *promoted* (allowed to
weigh in the final blended value) only if its median absolute percentage error on a
random sample of TEST_YEAR sales beats the comparables baseline on the same sales.
"""
from __future__ import annotations

import logging
import math
import random
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import joblib
import lightgbm as lgb
import numpy as np
from pymongo import MongoClient

import model_store
from estimator import LOOKBACK_YEARS, NoDataError, estimate_from_candidates, haversine_m
from models import MlFactor, MlResult

logger = logging.getLogger("ml_model")

MODEL_NAME = "ml_lgbm_v1"
MODEL_PATH = Path(__file__).parent / "data" / "models" / "lgbm_v1.joblib"
FEATURES = ["log_surface", "rooms", "log_land", "maison", "lat", "lon", "year_frac", "commune_pm2", "dept_pm2"]
GROUPS = {
    "log_surface": ("surface", "Surface"), "rooms": ("rooms", "Nombre de pièces"), "log_land": ("land", "Terrain"),
    "maison": ("type", "Type de bien"), "lat": ("location", "Localisation"), "lon": ("location", "Localisation"),
    "commune_pm2": ("location", "Localisation"), "dept_pm2": ("location", "Localisation"),
    "year_frac": ("time", "Période de marché"),
}
BASELINE_SAMPLE = 300

_lock = threading.Lock()
_training = False
_cache: dict = {}


def is_training() -> bool:
    return _training


def _year_frac(d: datetime) -> float:
    return d.year + (d.timetuple().tm_yday - 1) / 365.25


def _encode(rows: list[dict], commune_map: dict, dept_map: dict, year_frac: Optional[float] = None) -> np.ndarray:
    X = np.zeros((len(rows), len(FEATURES)))
    for i, r in enumerate(rows):
        maison = 1.0 if r["type"] == "maison" else 0.0
        lon, lat = r["location"]["coordinates"]
        key = (r["code_commune"], r["type"])
        dkey = (r["code_commune"][:2], r["type"])
        dept_pm2 = dept_map.get(dkey, dept_map.get("__all__", 7.0))
        X[i] = [
            math.log(r["surface"]), float(min(max(r.get("rooms") or 3, 1), 10)),
            math.log1p(min(max(r.get("land_surface") or 0.0, 0.0), 20000)) * maison, maison, lat, lon,
            year_frac if year_frac is not None else _year_frac(r["date"]),
            commune_map.get(key, dept_pm2), dept_pm2,
        ]
    return X


def _target_maps(rows: list[dict]) -> tuple[dict, dict]:
    by_c: dict = {}
    by_d: dict = {}
    for r in rows:
        v = math.log(r["price_m2"])
        by_c.setdefault((r["code_commune"], r["type"]), []).append(v)
        by_d.setdefault((r["code_commune"][:2], r["type"]), []).append(v)
    dept_map = {k: float(np.median(v)) for k, v in by_d.items()}
    dept_map["__all__"] = float(np.median([math.log(r["price_m2"]) for r in rows]))
    commune_map = {}
    for k, v in by_c.items():
        if len(v) >= 8:
            d = dept_map.get((k[0][:2], k[1]), dept_map["__all__"])
            w = len(v) / (len(v) + 10.0)
            commune_map[k] = w * float(np.median(v)) + (1 - w) * d
    return commune_map, dept_map


def _fit(X: np.ndarray, y: np.ndarray) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(n_estimators=700, learning_rate=0.04, num_leaves=63, min_child_samples=25,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.85, reg_lambda=1.0,
                              random_state=42, verbose=-1)
    model.fit(X, y)
    return model


def _metrics(pred_log: np.ndarray, y_log: np.ndarray) -> dict:
    ape = np.abs(np.exp(pred_log) - np.exp(y_log)) / np.exp(y_log)
    return {"n": int(len(y_log)), "mape": round(float(ape.mean() * 100), 1),
            "median_ape": round(float(np.median(ape) * 100), 1),
            "within_15pct": round(float((ape <= 0.15).mean() * 100), 1),
            "rmse_log": round(float(np.sqrt(np.mean((pred_log - y_log) ** 2))), 4)}


def _fetch_candidates_sync(db, lat: float, lon: float, code_commune: str, ptype: str, exclude: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=365 * LOOKBACK_YEARS)
    proj = {"mutation_id": 1, "date": 1, "price": 1, "surface": 1, "rooms": 1, "land_surface": 1, "price_m2": 1,
            "commune": 1, "code_commune": 1, "type": 1, "location": 1}
    base = {"type": ptype, "date": {"$gte": since}, "mutation_id": {"$ne": exclude}}
    near = list(db.dvf_sales.find({**base, "location": {"$nearSphere": {
        "$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": 5000}}}, proj).limit(3000))
    commune = list(db.dvf_sales.find({**base, "code_commune": code_commune}, proj).limit(3000))
    seen = {c["_id"]: c for c in near + commune}
    now = datetime.now(timezone.utc)
    out = []
    for c in seen.values():
        clon, clat = c["location"]["coordinates"]
        c["distance_m"] = haversine_m(lat, lon, clat, clon)
        d = c["date"] if c["date"].tzinfo else c["date"].replace(tzinfo=timezone.utc)
        c["age_years"] = (now - d).days / 365.25
        out.append(c)
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
        rows = list(db.dvf_sales.find({}, {"mutation_id": 1, "price": 1, "price_m2": 1, "surface": 1, "rooms": 1,
                                           "land_surface": 1, "type": 1, "code_commune": 1, "commune": 1,
                                           "year": 1, "date": 1, "location": 1}))
        if len(rows) < 1000:
            logger.warning("Not enough rows for ML (%d)", len(rows))
            return
        test_year = max(r["year"] for r in rows)
        train_rows = [r for r in rows if r["year"] < test_year]
        test_rows = [r for r in rows if r["year"] == test_year]

        # --- temporal validation ---
        cmap, dmap = _target_maps(train_rows)
        Xtr, ytr = _encode(train_rows, cmap, dmap), np.array([math.log(r["price"]) for r in train_rows])
        Xte, yte = _encode(test_rows, cmap, dmap), np.array([math.log(r["price"]) for r in test_rows])
        m_val = _fit(Xtr, ytr)
        pred_te = m_val.predict(Xte)
        holdout = _metrics(pred_te, yte)
        holdout["test_year"] = test_year
        by_type = {}
        for t in ("appartement", "maison"):
            idx = [i for i, r in enumerate(test_rows) if r["type"] == t]
            if idx:
                by_type[t] = _metrics(pred_te[idx], yte[idx])
        by_dept = {}
        for d in sorted({r["code_commune"][:2] for r in test_rows}):
            idx = [i for i, r in enumerate(test_rows) if r["code_commune"][:2] == d]
            if idx:
                by_dept[d] = _metrics(pred_te[idx], yte[idx])

        # --- gate: ML vs comparables baseline on the same sampled test sales ---
        rng = random.Random(42)
        sample_idx = rng.sample(range(len(test_rows)), min(BASELINE_SAMPLE, len(test_rows)))
        ml_ape, base_ape = [], []
        for i in sample_idx:
            r = test_rows[i]
            lon, lat = r["location"]["coordinates"]
            try:
                cands = _fetch_candidates_sync(db, lat, lon, r["code_commune"], r["type"], r["mutation_id"])
                est = estimate_from_candidates(cands, surface=r["surface"], ptype=r["type"], condition="correct",
                                               year_built=None,
                                               land_surface=r.get("land_surface") if r["type"] == "maison" else None,
                                               code_commune=r["code_commune"])
            except NoDataError:
                continue
            base_ape.append(abs(est.value - r["price"]) / r["price"])
            ml_ape.append(abs(math.exp(pred_te[i]) - r["price"]) / r["price"])
        gate = {
            "n": len(ml_ape),
            "ml_median_ape": round(float(np.median(ml_ape)) * 100, 1) if ml_ape else None,
            "baseline_median_ape": round(float(np.median(base_ape)) * 100, 1) if base_ape else None,
            "ml_mape": round(float(np.mean(ml_ape)) * 100, 1) if ml_ape else None,
            "baseline_mape": round(float(np.mean(base_ape)) * 100, 1) if base_ape else None,
        }
        promoted = bool(ml_ape and gate["ml_median_ape"] < gate["baseline_median_ape"])

        # --- production model on all data ---
        cmap_all, dmap_all = _target_maps(rows)
        Xall, yall = _encode(rows, cmap_all, dmap_all), np.array([math.log(r["price"]) for r in rows])
        m_all = _fit(Xall, yall)
        last_date = max(r["date"] for r in rows)
        importance = {f: int(v) for f, v in zip(FEATURES, m_all.feature_importances_)}
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": m_all, "commune_map": cmap_all, "dept_map": dmap_all,
                     "year_frac": _year_frac(last_date), "features": FEATURES}, MODEL_PATH)
        meta = {
            "_id": MODEL_NAME, "name": MODEL_NAME, "algorithm": "LightGBM", "n": len(rows), "n_train": len(train_rows),
            "n_test": len(test_rows), "features": FEATURES, "holdout": holdout, "by_type": by_type, "by_dept": by_dept,
            "gate": gate, "promoted": promoted, "feature_importance": importance,
            "trained_at": datetime.now(timezone.utc), "data_until": last_date,
        }
        db.models.replace_one({"_id": MODEL_NAME}, meta, upsert=True)
        model_store.dump(MODEL_NAME, meta)
        _cache.clear()
        logger.info("ML trained: holdout %s | gate %s | promoted=%s", holdout, gate, promoted)
    except Exception:  # noqa: BLE001
        logger.exception("ML training failed")
    finally:
        _training = False
        client.close()


async def load_meta(db) -> Optional[dict]:
    return await db.models.find_one({"_id": MODEL_NAME})


def _load_bundle() -> Optional[dict]:
    if not MODEL_PATH.exists():
        return None
    mtime = MODEL_PATH.stat().st_mtime
    if _cache.get("mtime") != mtime:  # (re)load when the file was (re)written, e.g. by a training subprocess
        _cache.clear()
        _cache["bundle"] = joblib.load(MODEL_PATH)
        _cache["mtime"] = mtime
    return _cache["bundle"]


def predict(meta: dict, *, surface: float, rooms: int, land: Optional[float], ptype: str, code_commune: str,
            lat: float, lon: float, condition_pct: float, year_pct: float) -> Optional[MlResult]:
    bundle = _load_bundle()
    if not bundle:
        return None
    row = {"surface": surface, "rooms": rooms, "land_surface": land, "type": ptype, "code_commune": code_commune,
           "location": {"coordinates": [lon, lat]}}
    X = _encode([row], bundle["commune_map"], bundle["dept_map"], year_frac=bundle["year_frac"])
    log_pred = float(bundle["model"].predict(X)[0])
    # Native LightGBM SHAP values (TreeSHAP): one contribution per feature, last column = expected value.
    contrib = bundle["model"].predict(X, pred_contrib=True)[0]
    sv, base = contrib[:-1], float(contrib[-1])
    grouped: dict[str, float] = {}
    labels: dict[str, str] = {}
    for f, v in zip(FEATURES, sv):
        g, label = GROUPS[f]
        grouped[g] = grouped.get(g, 0.0) + float(v)
        labels[g] = label
    factors = [MlFactor(key=g, label=labels[g], pct=round(math.exp(v) - 1, 4)) for g, v in
               sorted(grouped.items(), key=lambda kv: -abs(kv[1]))]
    value = math.exp(log_pred) * (1 + condition_pct) * (1 + year_pct)
    half = ((meta.get("holdout") or {}).get("median_ape") or 20.0) / 100.0
    gate = meta.get("gate") or {}
    return MlResult(
        model_version=MODEL_NAME, promoted=bool(meta.get("promoted")),
        value=float(int(round(value / 1000)) * 1000), low=float(int(round(value * (1 - half) / 1000)) * 1000),
        high=float(int(round(value * (1 + half) / 1000)) * 1000), price_m2=float(int(round(value / surface / 10)) * 10),
        reference_value=float(int(round(math.exp(base) / 1000)) * 1000), factors=factors,
        model_median_ape=gate.get("ml_median_ape"), baseline_median_ape=gate.get("baseline_median_ape"),
    )
