"""Heavy background jobs run in a separate *process* so the API (and platform health probes) stay responsive
while pandas/LightGBM saturate the CPU. Progress is tracked in MongoDB (dvf_meta / models), not in memory."""
from __future__ import annotations

import logging
import multiprocessing
from typing import Optional

logger = logging.getLogger("jobs")
_proc: Optional[multiprocessing.Process] = None


def _low_priority(delay_s: float) -> None:
    """Let the API finish booting and pass health probes before saturating CPU; then run niced."""
    import os
    import time

    time.sleep(delay_s)
    try:
        os.nice(10)
    except OSError:
        pass


def ingest_then_train(mongo_url: str, db_name: str, depts: list[str], years: list[int], delay_s: float = 45.0) -> None:
    import communes
    import dvf_ingest
    import model_store

    logging.basicConfig(level=logging.INFO)
    _low_priority(delay_s)
    communes.refresh_populations(mongo_url, db_name, depts)
    dvf_ingest.ingest_all(mongo_url, db_name, depts, years)
    # Fresh deployment: prefer the shipped artifacts (cheap) over retraining (~600 MB peak).
    seeded = set(model_store.seed_missing_sync(mongo_url, db_name))
    train_models(mongo_url, db_name, "hedonic_v2" not in seeded and _missing(mongo_url, db_name, "hedonic_v2"),
                 "ml_lgbm_v1" not in seeded and _missing(mongo_url, db_name, "ml_lgbm_v1"), delay_s=0.0)


def _missing(mongo_url: str, db_name: str, model_id: str) -> bool:
    from pymongo import MongoClient

    client = MongoClient(mongo_url)
    try:
        return client[db_name].models.find_one({"_id": model_id}, {"_id": 1}) is None
    finally:
        client.close()


def train_models(mongo_url: str, db_name: str, hedonic_missing: bool, ml_missing: bool, delay_s: float = 30.0) -> None:
    if not (hedonic_missing or ml_missing):
        return
    import hedonic
    import ml_model

    logging.basicConfig(level=logging.INFO)
    _low_priority(delay_s)
    if hedonic_missing:
        hedonic.train(mongo_url, db_name)
    if ml_missing:
        ml_model.train(mongo_url, db_name)


def retrain(mongo_url: str, db_name: str, which: str) -> None:
    """Explicit retraining requested from the settings screen (always in a child process)."""
    train_models(mongo_url, db_name, which == "hedonic", which == "ml", delay_s=0.0)


def is_running() -> bool:
    return _proc is not None and _proc.is_alive()


def start(target, *args) -> bool:
    """Start `target(*args)` in a spawned process; returns False if a job is already running."""
    global _proc
    if is_running():
        return False
    _proc = multiprocessing.get_context("spawn").Process(target=target, args=args, daemon=True)
    _proc.start()
    logger.info("Background job %s started (pid %s)", target.__name__, _proc.pid)
    return True
