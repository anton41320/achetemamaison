"""Emergent managed Object Storage client (sync requests; call via asyncio.to_thread)."""
from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger("storage")

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "estimo"
_storage_key: str | None = None


class StorageError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    if resp.status_code != 200:
        raise StorageError(resp.status_code, f"Stockage indisponible ({resp.status_code})")
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _reset():
    global _storage_key
    _storage_key = None


def put_object(path: str, data: bytes, content_type: str) -> dict:
    for attempt in range(2):
        key = init_storage()
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type},
                            data=data, timeout=120)
        if resp.status_code == 503 and attempt == 0:
            _reset()
            continue
        if resp.status_code == 402:
            raise StorageError(402, "Crédits de stockage épuisés : rechargez la clé universelle.")
        if resp.status_code != 200:
            raise StorageError(resp.status_code, f"Échec de l'envoi ({resp.status_code})")
        return resp.json()
    raise StorageError(503, "Stockage temporairement indisponible")


def get_object(path: str) -> tuple[bytes, str]:
    for attempt in range(2):
        key = init_storage()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
        if resp.status_code == 503 and attempt == 0:
            _reset()
            continue
        if resp.status_code != 200:
            raise StorageError(resp.status_code, f"Fichier indisponible ({resp.status_code})")
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    raise StorageError(503, "Stockage temporairement indisponible")
