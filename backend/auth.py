"""Authentification email + mot de passe (JWT Bearer, Argon2) — inscription, connexion, mot de passe oublié
(lien + code à 6 chiffres par email), changement de mot de passe, suppression de compte.

Le premier compte créé récupère toutes les données existantes sans propriétaire (biens de la phase sans compte)."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Optional
from urllib.parse import urlparse

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field

import emailer
import telegram_notify

logger = logging.getLogger("auth")

JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_hex(32)
JWT_ALG = "HS256"
JWT_DAYS = 30            # application mobile : session longue, révoquée si le compte disparaît
RESET_MINUTES = 15
OWNED_COLLECTIONS = ("properties", "documents", "photos", "listings", "orders")

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
current_user_var: ContextVar[Optional[dict]] = ContextVar("current_user", default=None)
router = APIRouter(prefix="/api/auth")
_db = None


def init(db) -> None:
    global _db
    _db = db


async def ensure_indexes() -> None:
    await _db.users.create_index("email", unique=True)
    await _db.password_resets.create_index("expires_at", expireAfterSeconds=0)
    for coll in OWNED_COLLECTIONS:
        await _db[coll].create_index("owner_id")


def now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def make_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": now() + timedelta(days=JWT_DAYS), "iat": now()}, JWT_SECRET, algorithm=JWT_ALG)


def public_user(u: dict) -> dict:
    return {"id": str(u["_id"]), "email": u["email"], "created_at": u["created_at"]}


async def _user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        uid = ObjectId(payload["sub"])
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Session invalide ou expirée, reconnectez-vous")
    user = await _db.users.find_one({"_id": uid})
    if not user:
        raise HTTPException(status_code=401, detail="Ce compte n'existe plus")
    return user


async def require_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
                       t: Optional[str] = Query(default=None, include_in_schema=False)) -> dict:
    """Bearer header, or `?t=` query token for PDF/file links opened by the OS (no headers possible)."""
    token = creds.credentials if creds else t
    if not token:
        raise HTTPException(status_code=401, detail="Connexion requise")
    user = await _user_from_token(token)
    current_user_var.set(user)
    return user


def owner_id() -> str:
    user = current_user_var.get()
    if not user:
        raise HTTPException(status_code=401, detail="Connexion requise")
    return str(user["_id"])


def own() -> dict:
    """Mongo filter fragment restricting a query to the current user's records."""
    return {"owner_id": owner_id()}


# ---------------- Schemas ----------------

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotIn(BaseModel):
    email: EmailStr
    origin: str = Field(min_length=8, max_length=300)


class ResetIn(BaseModel):
    token_or_code: str = Field(min_length=6, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class DeleteIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


# ---------------- Endpoints ----------------

@router.post("/register", status_code=201)
async def register(body: Credentials):
    email = body.email.lower().strip()
    if await _db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")
    first_account = await _db.users.estimated_document_count() == 0
    try:
        res = await _db.users.insert_one({"email": email, "password_hash": passwords.hash(body.password),
                                          "created_at": now(), "updated_at": now()})
    except Exception:  # noqa: BLE001 — unique index race
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")
    uid = str(res.inserted_id)
    if first_account:
        # Migration : les données créées avant l'authentification appartiennent au premier compte.
        for coll in OWNED_COLLECTIONS:
            r = await _db[coll].update_many({"owner_id": {"$exists": False}}, {"$set": {"owner_id": uid}})
            if r.modified_count:
                logger.info("Attributed %d %s to first account", r.modified_count, coll)
    user = await _db.users.find_one({"_id": res.inserted_id})
    telegram_notify.new_user(email, await _db.users.estimated_document_count())
    return {"access_token": make_token(uid), "token_type": "bearer", "user": public_user(user)}


@router.post("/login")
async def login(body: Credentials):
    user = await _db.users.find_one({"email": body.email.lower().strip()})
    valid = passwords.verify(body.password, user["password_hash"] if user else passwords.hash("timing-dummy-password"))
    if not user or not valid:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return {"access_token": make_token(str(user["_id"])), "token_type": "bearer", "user": public_user(user)}


@router.get("/me")
async def me(user: dict = Depends(require_user)):
    return public_user(user)


@router.post("/change-password")
async def change_password(body: ChangePassword, user: dict = Depends(require_user)):
    if not passwords.verify(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    await _db.users.update_one({"_id": user["_id"]}, {"$set": {"password_hash": passwords.hash(body.new_password), "updated_at": now()}})
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn, request: Request):
    """Toujours la même réponse (pas d'énumération). Envoie un lien + un code à 6 chiffres valables 15 min."""
    email = body.email.lower().strip()
    user = await _db.users.find_one({"email": email})
    parsed = urlparse(body.origin)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Origine invalide")
    origin = f"https://{parsed.netloc}"
    if user:
        recent = await _db.password_resets.count_documents({"user_id": user["_id"], "created_at": {"$gt": now() - timedelta(minutes=5)}})
        if recent < 3 and emailer.email_ready():
            raw = secrets.token_urlsafe(32)
            code = f"{secrets.randbelow(1_000_000):06d}"
            await _db.password_resets.insert_one({"user_id": user["_id"], "token_hash": _digest(raw), "code_hash": _digest(code),
                                                  "expires_at": now() + timedelta(minutes=RESET_MINUTES), "used_at": None, "created_at": now()})
            link = f"{origin}/reset-password?token={raw}"
            brand = escape(emailer.EMAIL_FROM_NAME)
            html = (
                '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fb;padding:24px 0"><tr><td align="center">'
                '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;font-family:Arial,Helvetica,sans-serif;color:#0f1f3d">'
                f'<tr><td style="padding:28px 32px 8px"><p style="margin:0;font-size:20px;font-weight:bold;color:#1656C9">{brand}</p>'
                '<p style="margin:4px 0 0;font-size:13px;color:#6b7772">Réinitialisation du mot de passe</p></td></tr>'
                '<tr><td style="padding:16px 32px"><p style="margin:0 0 12px;font-size:15px;line-height:22px">Vous avez demandé à réinitialiser votre mot de passe. '
                f'Ce lien et ce code expirent dans {RESET_MINUTES} minutes.</p>'
                f'<p style="margin:16px 0"><a href="{link}" style="display:inline-block;background:#1656C9;color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold;font-size:14px">Choisir un nouveau mot de passe</a></p>'
                f'<p style="margin:0 0 6px;font-size:14px">Depuis l’application, saisissez ce code&nbsp;:</p>'
                f'<p style="margin:0 0 16px;font-size:28px;letter-spacing:6px;font-weight:bold;color:#1656C9">{code}</p>'
                '<p style="margin:0;font-size:13px;color:#6b7772">Si vous n’êtes pas à l’origine de cette demande, ignorez cet email : votre mot de passe reste inchangé.</p></td></tr>'
                f'<tr><td style="padding:12px 32px 24px;font-size:12px;color:#8a948f;line-height:18px">Envoyé par {brand}. Nous ne vous demanderons jamais votre mot de passe par email.</td></tr>'
                '</table></td></tr></table>'
            )
            try:
                await emailer.send_email(to=email, subject=f"{emailer.EMAIL_FROM_NAME} — réinitialisez votre mot de passe", html=html)
            except Exception:  # noqa: BLE001
                logger.exception("Password reset email failed")
    return {"ok": True, "message": "Si un compte existe pour cet email, un lien et un code viennent d'être envoyés."}


@router.post("/reset-password")
async def reset_password(body: ResetIn):
    key = _digest(body.token_or_code.strip())
    record = await _db.password_resets.find_one_and_update(
        {"$or": [{"token_hash": key}, {"code_hash": key}], "used_at": None, "expires_at": {"$gt": now()}},
        {"$set": {"used_at": now()}})
    if not record:
        raise HTTPException(status_code=400, detail="Lien ou code invalide ou expiré")
    await _db.users.update_one({"_id": record["user_id"]}, {"$set": {"password_hash": passwords.hash(body.new_password), "updated_at": now()}})
    user = await _db.users.find_one({"_id": record["user_id"]})
    return {"ok": True, "access_token": make_token(str(user["_id"])), "token_type": "bearer", "user": public_user(user)}


async def erase_user(user: dict) -> None:
    """Données du vendeur passées en suppression logique, compte et jetons effacés (in-app et page web)."""
    uid = str(user["_id"])
    for coll in ("properties", "documents", "photos", "listings"):
        await _db[coll].update_many({"owner_id": uid, "deleted_at": None}, {"$set": {"deleted_at": now()}})
    await _db.password_resets.delete_many({"user_id": user["_id"]})
    await _db.account_deletions.delete_many({"user_id": user["_id"]})
    await _db.users.delete_one({"_id": user["_id"]})


@router.delete("/account")
async def delete_account(body: DeleteIn, user: dict = Depends(require_user)):
    """Suppression de compte (exigence App Store) depuis l'application."""
    if not passwords.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect")
    await erase_user(user)
    return {"ok": True}


async def request_web_deletion(email: str, origin: str) -> None:
    """Page web « supprimer mon compte » (exigence Google Play) : lien de confirmation par e-mail, valable 15 min."""
    user = await _db.users.find_one({"email": email.lower().strip()})
    if not user or not emailer.email_ready():
        return
    recent = await _db.account_deletions.count_documents({"user_id": user["_id"], "created_at": {"$gt": now() - timedelta(minutes=5)}})
    if recent >= 3:
        return
    raw = secrets.token_urlsafe(32)
    await _db.account_deletions.insert_one({"user_id": user["_id"], "token_hash": _digest(raw),
                                            "expires_at": now() + timedelta(minutes=RESET_MINUTES), "created_at": now()})
    link = f"{origin}/api/account/delete/confirm?token={raw}"
    brand = escape(emailer.EMAIL_FROM_NAME)
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fb;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;font-family:Arial,Helvetica,sans-serif;color:#0f1f3d">'
        f'<tr><td style="padding:28px 32px 8px"><p style="margin:0;font-size:20px;font-weight:bold;color:#1656C9">{brand}</p>'
        '<p style="margin:4px 0 0;font-size:13px;color:#6b7772">Suppression de votre compte</p></td></tr>'
        '<tr><td style="padding:16px 32px"><p style="margin:0 0 12px;font-size:15px;line-height:22px">Vous avez demandé la suppression de votre compte et de toutes '
        f'les données associées (biens, estimations, documents, photos, annonces). Cette action est définitive. Le lien expire dans {RESET_MINUTES} minutes.</p>'
        f'<p style="margin:16px 0"><a href="{link}" style="display:inline-block;background:#D9342B;color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold;font-size:14px">Confirmer la suppression définitive</a></p>'
        '<p style="margin:0;font-size:13px;color:#6b7772">Si vous n’êtes pas à l’origine de cette demande, ignorez cet e-mail : rien ne sera supprimé.</p></td></tr>'
        '</table></td></tr></table>'
    )
    try:
        await emailer.send_email(to=user["email"], subject=f"{emailer.EMAIL_FROM_NAME} — confirmez la suppression de votre compte", html=html)
    except Exception:  # noqa: BLE001
        logger.exception("Account deletion email failed")


async def confirm_web_deletion(token: str) -> bool:
    row = await _db.account_deletions.find_one({"token_hash": _digest(token), "expires_at": {"$gt": now()}})
    if not row:
        return False
    user = await _db.users.find_one({"_id": row["user_id"]})
    if user:
        await erase_user(user)
    else:
        await _db.account_deletions.delete_many({"user_id": row["user_id"]})
    return True
