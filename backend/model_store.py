"""Model artifacts shipped with the code (backend/data/models/*.json).

The deployment target is memory-constrained: training LightGBM/hedonic models in the container
peaks at ~600 MB. Models are therefore trained once (preview environment), exported to disk and
committed; a fresh deployment simply seeds MongoDB from these files instead of retraining."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient

logger = logging.getLogger("model_store")

MODELS_DIR = Path(__file__).parent / "data" / "models"
# model _id -> exported file
ARTIFACTS = {
    "hedonic_v2": MODELS_DIR / "hedonic_v2.json",
    "ml_lgbm_v1": MODELS_DIR / "lgbm_v1.meta.json",
}


def _encode(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return {"__dt__": obj.isoformat()}
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_encode(v) for v in obj]
    return obj


def _decode(obj: Any) -> Any:
    if isinstance(obj, dict):
        if set(obj.keys()) == {"__dt__"}:
            return datetime.fromisoformat(obj["__dt__"])
        return {k: _decode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode(v) for v in obj]
    return obj


def dump(model_id: str, doc: dict) -> None:
    path = ARTIFACTS[model_id]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_encode({**doc, "_id": model_id}), ensure_ascii=False))
    logger.info("Model %s exported to %s", model_id, path.name)


def load(model_id: str) -> dict | None:
    path = ARTIFACTS[model_id]
    if not path.exists():
        return None
    return _decode(json.loads(path.read_text()))


def seed_missing_sync(mongo_url: str, db_name: str) -> list[str]:
    """Insert every shipped model that is absent from `models`; returns the ids seeded."""
    client = MongoClient(mongo_url)
    try:
        return seed_missing_with(client[db_name])
    finally:
        client.close()


def _ts(value: Any) -> float:
    """trained_at → epoch seconds (naive Mongo datetimes are UTC ; missing → 0)."""
    if not isinstance(value, datetime):
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def seed_missing_with(db) -> list[str]:
    """Seed shipped models that are absent from `models` — or older than the shipped artifact (e.g. retrained on more départements)."""
    seeded: list[str] = []
    for model_id in ARTIFACTS:
        doc = load(model_id)
        if not doc:
            continue
        current = db.models.find_one({"_id": model_id}, {"trained_at": 1})
        if current and not (_ts(doc.get("trained_at")) > _ts(current.get("trained_at"))):
            continue
        db.models.replace_one({"_id": model_id}, doc, upsert=True)
        seeded.append(model_id)
        logger.info("Model %s seeded from disk (%s)", model_id, "newer artifact" if current else "missing")
    return seeded
