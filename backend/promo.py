"""Codes promo testeurs : un code (PROMO_CODES=AMM-XXXX-XX,…) débloque le Pack premium sur tous les biens d'un compte.

Chaque code est à usage unique : la première utilisation est enregistrée dans `promo_redemptions` et le code est
attaché au compte (`users.promo_code`). Idempotent pour le compte qui l'a déjà utilisé.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import auth

router = APIRouter(prefix="/promo", tags=["promo"])
_db = None


def init(db) -> None:
    global _db
    _db = db


def valid_codes() -> set[str]:
    return {normalize(c) for c in os.environ.get("PROMO_CODES", "").split(",") if c.strip()}


def normalize(code: str) -> str:
    return re.sub(r"[\s_]+", "", code).upper().replace("—", "-").replace("–", "-")


def user_has_promo(user: dict | None) -> bool:
    return bool(user and user.get("promo_code"))


class RedeemIn(BaseModel):
    code: str = Field(min_length=4, max_length=40)


@router.post("/redeem")
async def redeem(body: RedeemIn):
    user = auth.current_user_var.get()
    code = normalize(body.code)
    if code not in valid_codes():
        raise HTTPException(status_code=404, detail="Code invalide. Vérifiez les caractères (ex. AMM-7K3P-Q2).")
    existing = await _db.promo_redemptions.find_one({"code": code})
    if existing and existing["user_id"] != str(user["_id"]):
        raise HTTPException(status_code=409, detail="Ce code a déjà été utilisé par un autre compte.")
    if not existing:
        await _db.promo_redemptions.insert_one({"code": code, "user_id": str(user["_id"]), "email": user.get("email"),
                                                "redeemed_at": datetime.now(timezone.utc)})
    await _db.users.update_one({"_id": user["_id"]}, {"$set": {"promo_code": code, "promo_redeemed_at": datetime.now(timezone.utc)}})
    return {"unlocked": True, "code": code}


@router.get("/status")
async def status():
    user = auth.current_user_var.get()
    return {"active": user_has_promo(user), "code": (user or {}).get("promo_code")}
