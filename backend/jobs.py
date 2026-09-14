"""Heavy background jobs run in a separate *process* so the API (and platform health probes) stay responsive
while pandas/LightGBM saturate the CPU. Progress is tracked in MongoDB (dvf_meta / models), not in memory."""
from __future__ import annotations

import logging
import multiprocessing
from typing import Optional

logger = logging.getLogger("jobs")
_proc: Optional[multiprocessing.Process] = None


def ingest_then_train(mongo_url: str, db_name: str, depts: list[str], years: list[int]) -> None:
    import communes
    import dvf_ingest
    import hedonic
    import ml_model

    logging.basicConfig(level=logging.INFO)
    communes.refresh_populations(mongo_url, db_name, depts)
    dvf_ingest.ingest_all(mongo_url, db_name, depts, years)
    hedonic.train(mongo_url, db_name)
    ml_model.train(mongo_url, db_name)


def train_models(mongo_url: str, db_name: str, hedonic_missing: bool, ml_missing: bool) -> None:
    import hedonic
    import ml_model

    logging.basicConfig(level=logging.INFO)
    if hedonic_missing:
        hedonic.train(mongo_url, db_name)
    if ml_missing:
        ml_model.train(mongo_url, db_name)


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
