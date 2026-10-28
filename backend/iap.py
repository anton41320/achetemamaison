"""Achat intégré (Apple / Google) via RevenueCat pour le Pack premium — mobile uniquement (Stripe reste pour le web).

Modèle : produit consommable `pack_premium_49`, un achat par bien. Le serveur est la source de vérité :
chaque transaction vérifiée devient une commande `orders` {provider: "revenuecat", status: "paid"} rattachée au bien,
ce qui débloque les outils IA via `pack.is_unlocked`.

Rattachement transaction → bien :
  1. attribut abonné RevenueCat `property_id` (posé par l'app avant l'achat, transmis dans le webhook) ;
  2. sinon, dernière « intention d'achat » en attente de l'utilisateur (`iap_intents`).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import auth
from pack import PACK_CURRENCY, PACK_PRICE_CENTS

logger = logging.getLogger("iap")

PRODUCT_ID = "pack_premium_49"
PURCHASE_EVENTS = {"INITIAL_PURCHASE", "NON_RENEWING_PURCHASE"}
REFUND_EVENTS = {"CANCELLATION", "EXPIRATION"}
WEBHOOK_SECRET = os.environ.get("REVENUECAT_WEBHOOK_SECRET", "")
SECRET_KEY = os.environ.get("REVENUECAT_SECRET_KEY", "")  # facultatif : vérification côté serveur (claim)
RC_API = "https://api.revenuecat.com/v1"

router = APIRouter(prefix="/iap")
webhook_router = APIRouter()
_db = None


def init(db) -> None:
    global _db
    _db = db


async def ensure_indexes() -> None:
    await _db.orders.create_index("transaction_id", unique=True, sparse=True)
    await _db.iap_intents.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
    await _db.iap_events.create_index("event_id", unique=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class IntentIn(BaseModel):
    property_id: str


class ClaimIn(BaseModel):
    property_id: str


async def _own_property(pid: str, user: dict) -> dict:
    from bson import ObjectId

    try:
        oid = ObjectId(pid)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Bien introuvable")
    doc = await _db.properties.find_one({"_id": oid, "deleted_at": None, "owner_id": str(user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return doc


@router.post("/intents", status_code=201)
async def create_intent(body: IntentIn, user: dict = Depends(auth.require_user)):
    """À appeler juste avant d'ouvrir la feuille d'achat : mémorise « cet utilisateur achète pour ce bien »."""
    await _own_property(body.property_id, user)
    uid = str(user["_id"])
    await _db.iap_intents.update_many({"user_id": uid, "status": "pending"}, {"$set": {"status": "superseded"}})
    await _db.iap_intents.insert_one({"user_id": uid, "property_id": body.property_id, "product_id": PRODUCT_ID,
                                      "status": "pending", "created_at": _now()})
    return {"ok": True, "product_id": PRODUCT_ID, "app_user_id": uid}


async def grant(uid: str, property_id: str, transaction_id: str, environment: str | None, store: str | None,
                price_cents: int | None = None, currency: str | None = None) -> bool:
    """Crée la commande payée (idempotent sur transaction_id). Retourne True si nouvellement créée."""
    if await _db.orders.find_one({"transaction_id": transaction_id}, {"_id": 1}):
        return False
    try:
        await _db.orders.insert_one({"property_id": property_id, "owner_id": uid, "provider": "revenuecat", "store": store,
                                     "transaction_id": transaction_id, "product_id": PRODUCT_ID, "environment": environment,
                                     "amount": price_cents or PACK_PRICE_CENTS, "currency": (currency or PACK_CURRENCY).lower(),
                                     "status": "paid", "paid_at": _now(), "created_at": _now(), "customer_email": None})
    except Exception:  # noqa: BLE001 — course avec un doublon de webhook
        return False
    logger.info("IAP grant property=%s tx=%s env=%s", property_id, transaction_id, environment)
    return True


def _signature_ok(raw: bytes, request: Request) -> bool:
    """Accepte l'en-tête Authorization configuré dans RevenueCat OU la signature HMAC (X-RevenueCat-Webhook-Signature)."""
    if not WEBHOOK_SECRET:
        return False
    auth_header = request.headers.get("authorization", "")
    if hmac.compare_digest(auth_header, WEBHOOK_SECRET) or hmac.compare_digest(auth_header, f"Bearer {WEBHOOK_SECRET}"):
        return True
    sig = request.headers.get("x-revenuecat-webhook-signature")
    if not sig:
        return False
    try:
        fields = dict(p.split("=", 1) for p in sig.split(","))
        ts, v1 = int(fields["t"]), fields["v1"]
        if abs(time.time() - ts) > 300:
            return False
        expected = hmac.new(WEBHOOK_SECRET.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
    except (KeyError, ValueError):
        return False


@webhook_router.post("/webhooks/revenuecat", include_in_schema=False)
async def revenuecat_webhook(request: Request):
    raw = await request.body()
    if not _signature_ok(raw, request):
        raise HTTPException(status_code=401, detail="Signature invalide")
    body = json.loads(raw or b"{}")
    event = body.get("event") or body
    event_id = event.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Événement sans id")
    try:
        await _db.iap_events.insert_one({"event_id": event_id, "type": event.get("type"), "received_at": _now(), "event": event})
    except Exception:  # noqa: BLE001 — doublon : déjà traité
        return {"ok": True, "duplicate": True}

    etype, product, tx = event.get("type"), event.get("product_id"), event.get("transaction_id")
    uid = event.get("app_user_id") or ""
    if etype in REFUND_EVENTS and tx:
        await _db.orders.update_one({"transaction_id": tx, "status": "paid"}, {"$set": {"status": "refunded", "refunded_at": _now()}})
        return {"ok": True, "refunded": True}
    if etype not in PURCHASE_EVENTS or product != PRODUCT_ID or not uid or not tx:
        return {"ok": True, "ignored": True}

    attrs = event.get("subscriber_attributes") or {}
    property_id = ((attrs.get("property_id") or {}).get("value") or "").strip() or None
    if not property_id:
        intent = await _db.iap_intents.find_one_and_update({"user_id": uid, "status": "pending"}, {"$set": {"status": "matched", "transaction_id": tx}},
                                                           sort=[("created_at", -1)])
        property_id = intent["property_id"] if intent else None
    if not property_id:
        logger.warning("IAP purchase without property: user=%s tx=%s", uid, tx)
        await _db.iap_events.update_one({"event_id": event_id}, {"$set": {"unmatched": True}})
        return {"ok": True, "unmatched": True}
    price = event.get("price_in_purchased_currency") or event.get("price")
    created = await grant(uid, property_id, tx, event.get("environment"), event.get("store"),
                          int(round(float(price) * 100)) if price else None, event.get("currency"))
    await _db.iap_intents.update_many({"user_id": uid, "status": "pending"}, {"$set": {"status": "matched", "transaction_id": tx}})
    return {"ok": True, "granted": created}


@router.post("/claim")
async def claim(body: ClaimIn, user: dict = Depends(auth.require_user)):
    """Filet de sécurité si le webhook tarde : vérifie l'achat auprès de RevenueCat (clé secrète serveur) et débloque le bien."""
    await _own_property(body.property_id, user)
    uid = str(user["_id"])
    if await _db.orders.find_one({"property_id": body.property_id, "status": "paid"}, {"_id": 1}):
        return {"unlocked": True}
    if not SECRET_KEY:
        return {"unlocked": False, "pending": True, "message": "Achat en cours de confirmation, réessayez dans un instant."}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{RC_API}/subscribers/{uid}", headers={"Authorization": f"Bearer {SECRET_KEY}"})
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=424, detail="Vérification de l'achat indisponible")
    purchases = ((r.json().get("subscriber") or {}).get("non_subscriptions") or {}).get(PRODUCT_ID) or []
    for p in purchases:
        tx = p.get("store_transaction_id") or p.get("id")
        if tx and not await _db.orders.find_one({"transaction_id": tx}, {"_id": 1}):
            await grant(uid, body.property_id, tx, "SANDBOX" if p.get("is_sandbox") else "PRODUCTION", p.get("store"))
            await _db.iap_intents.update_many({"user_id": uid, "status": "pending"}, {"$set": {"status": "matched", "transaction_id": tx}})
            return {"unlocked": True}
    return {"unlocked": False, "pending": True, "message": "Aucun achat non utilisé trouvé pour le moment."}
