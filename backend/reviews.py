"""Avis utilisateurs (étoiles + commentaire) : collecte dans l'app, modération par le gérant via Telegram, affichage public.

- `POST /api/reviews` : public (jeton Bearer facultatif) — un avis par compte (mise à jour) ou par appareil anonyme.
- `GET /api/public/reviews` : avis approuvés (site + app).
- `GET /api/reviews/{id}/moderate?a=approve|reject&k=…` : lien signé (HMAC du JWT_SECRET) envoyé dans l'alerte Telegram.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from html import escape
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import auth
import telegram_notify
from free_estimate import _origin

logger = logging.getLogger("reviews")
router = APIRouter(tags=["reviews"])
_db = None


def init(db) -> None:
    global _db
    _db = db


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=800)
    name: str = Field(default="", max_length=40)
    source: Literal["ios", "android", "web"] = "web"
    device_key: str = Field(default="", max_length=64)


def _sig(review_id: str, action: str) -> str:
    return hmac.new(auth.JWT_SECRET.encode(), f"{review_id}:{action}".encode(), hashlib.sha256).hexdigest()[:32]


def _public(r: dict) -> dict:
    return {"id": str(r["_id"]), "rating": r["rating"], "comment": r.get("comment", ""), "name": r.get("name") or "Un vendeur",
            "created_at": r["created_at"].isoformat()}


@router.post("/api/reviews")
async def submit_review(body: ReviewIn, request: Request, authorization: Optional[str] = Header(default=None)):
    user = None
    if authorization and authorization.lower().startswith("bearer "):
        try:
            user = await auth._user_from_token(authorization.split(" ", 1)[1])
        except HTTPException:
            user = None
    if not user and not body.device_key:
        raise HTTPException(status_code=400, detail="Identifiant d'appareil manquant")
    key = {"user_id": str(user["_id"])} if user else {"device_key": body.device_key}
    now = datetime.now(timezone.utc)
    doc = {**key, "rating": body.rating, "comment": body.comment.strip(), "name": body.name.strip(), "source": body.source,
           "email": (user or {}).get("email"), "status": "pending", "updated_at": now}
    res = await _db.reviews.find_one_and_update(key, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True, return_document=True)
    rid = str(res["_id"])
    origin = _origin(request)
    stars = "⭐" * body.rating + "☆" * (5 - body.rating)
    lines = [f"📝 <b>Nouvel avis</b> {stars} ({body.rating}/5) · {body.source}"]
    if body.name.strip():
        lines.append(f"👤 {escape(body.name.strip())}")
    if (user or {}).get("email"):
        lines.append(f"✉️ {escape(user['email'])}")
    if body.comment.strip():
        lines.append(f"💬 « {escape(body.comment.strip())} »")
    lines.append(f'<a href="{origin}/api/reviews/{rid}/moderate?a=approve&k={_sig(rid, "approve")}">✅ Approuver</a>  ·  '
                 f'<a href="{origin}/api/reviews/{rid}/moderate?a=reject&k={_sig(rid, "reject")}">🗑 Rejeter</a>')
    telegram_notify.notify("\n".join(lines))
    return {"id": rid, "status": "pending"}


@router.get("/api/reviews/{review_id}/moderate", include_in_schema=False, response_class=HTMLResponse)
async def moderate(review_id: str, a: Literal["approve", "reject"], k: str):
    if not hmac.compare_digest(k, _sig(review_id, a)):
        raise HTTPException(status_code=403, detail="Lien invalide")
    status = "approved" if a == "approve" else "rejected"
    res = await _db.reviews.update_one({"_id": ObjectId(review_id)}, {"$set": {"status": status, "moderated_at": datetime.now(timezone.utc)}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    label = "✅ Avis approuvé : il est maintenant visible publiquement." if status == "approved" else "🗑 Avis rejeté : il ne sera pas affiché."
    return f'<html lang="fr"><body style="font-family:sans-serif;padding:40px;text-align:center"><h2>{label}</h2></body></html>'


@router.get("/api/public/reviews")
async def public_reviews(limit: int = 20):
    cur = _db.reviews.find({"status": "approved"}, sort=[("created_at", -1)], limit=min(max(limit, 1), 50))
    items = [_public(r) async for r in cur]
    agg = await _db.reviews.aggregate([{"$match": {"status": "approved"}},
                                       {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]).to_list(1)
    stats = {"average": round(agg[0]["avg"], 1), "count": agg[0]["count"]} if agg else {"average": None, "count": 0}
    return {"items": items, **stats}
