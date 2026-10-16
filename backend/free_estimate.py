"""Estimation gratuite par e-mail (site public, sans compte).

`POST /api/public/free-estimate` {email, property} → estimation (même moteur que l'app) → rapport PDF (report.build_report)
conservé 90 jours (collection `free_estimates`, bytes du PDF + bien + estimation) → e-mail (Resend géré par Emergent) avec la
fourchette, un lien vers le PDF et un appel à créer un compte (`/sign-up?draft=<token>` : la fiche est reprise à l'inscription).
Garde-fous : 3 envois / e-mail / 24 h, 10 envois / IP / h, réponse identique en cas de refus de l'adresse par le service.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

import emailer
import report
from models import PropertyDoc, PropertyIn

log = logging.getLogger("free_estimate")
router = APIRouter(prefix="/api/public/free-estimate", tags=["public"])
db = None  # injecté par server.py
run_estimation = None  # injecté par server.py (server._run_estimation)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
TTL_DAYS = 90
MAX_PER_EMAIL_24H = 3
MAX_PER_IP_1H = 10
REMINDER_AFTER_DAYS = int(os.environ.get("FREE_ESTIMATE_REMINDER_DAYS", "3"))
REMINDER_INTERVAL_S = 3600


class FreeEstimateRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    property: PropertyIn


def _origin(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else None) or (request.client.host if request.client else "?")


async def ensure_indexes():
    await db.free_estimates.create_index("created_at", expireAfterSeconds=TTL_DAYS * 86400)
    await db.free_estimates.create_index("token", unique=True)
    await db.free_estimates.create_index([("email", 1), ("created_at", -1)])
    await db.free_estimates.create_index([("ip", 1), ("created_at", -1)])


def _email_html(*, origin: str, token: str, prop: PropertyIn, est, brand: str) -> tuple[str, str]:
    eur = report.eur
    pdf_url = f"{origin}/api/public/free-estimate/{token}.pdf"
    signup_url = f"{origin}/sign-up?draft={token}"
    ptype = "Maison" if prop.property_type == "maison" else "Appartement"
    subject = f"Votre estimation {brand} : {eur(est.value)} — {prop.address_label}"
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fb;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;padding:28px;'
        'font-family:Helvetica,Arial,sans-serif;color:#0f1f3d">'
        f'<tr><td><p style="margin:0 0 6px;font-size:13px;color:#1656c9;font-weight:bold;letter-spacing:1px">{escape(brand).upper()}</p>'
        f'<h1 style="margin:0 0 16px;font-size:22px">Votre estimation gratuite</h1>'
        f'<p style="margin:0 0 4px;font-size:14px;color:#51607a">{escape(prop.address_label)}</p>'
        f'<p style="margin:0 0 16px;font-size:14px;color:#51607a">{ptype} · {prop.surface:g} m² · {prop.rooms} pièces</p>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e8f0fd;border-radius:10px;padding:16px">'
        f'<tr><td><p style="margin:0;font-size:12px;color:#51607a;text-transform:uppercase;letter-spacing:1px">Valeur estimée</p>'
        f'<p style="margin:4px 0 6px;font-size:32px;font-weight:bold;color:#1656c9">{eur(est.value)}</p>'
        f'<p style="margin:0;font-size:14px">Fourchette {eur(est.low)} – {eur(est.high)} · {eur(est.price_m2)}/m² · '
        f'{est.confidence.n_comparables} ventes comparables ({escape(est.confidence.radius_label)})</p></td></tr></table>'
        f'<p style="margin:20px 0 8px;font-size:14px">Le rapport détaillé (calcul, ajustements, marché local) est joint sous forme de PDF :</p>'
        f'<p style="margin:0 0 20px"><a href="{pdf_url}" style="font-size:14px;color:#1656c9;font-weight:bold">Télécharger le rapport PDF</a></p>'
        '<p style="margin:0 0 12px;font-size:14px;line-height:21px">Créez votre compte gratuit pour retrouver cette estimation, consulter le '
        '<b>dossier environnement</b> de votre bien (écoles, commerces, transports, risques), les ventes comparables et préparer la vente '
        '(prix, photos, annonce, dossier de vente) — sur le site comme dans l’application mobile.</p>'
        f'<p style="margin:0 0 24px"><a href="{signup_url}" style="display:inline-block;background:#1656c9;color:#ffffff;text-decoration:none;'
        'font-weight:bold;font-size:15px;padding:12px 20px;border-radius:10px">Créer mon compte gratuit</a></p>'
        f'<p style="margin:0;font-size:11px;line-height:16px;color:#7b879c">{escape(report.LEGAL_DISCLAIMER[0])} '
        f'Ce lien PDF reste valable {TTL_DAYS} jours. Vous recevez cet e-mail parce que cette adresse a été saisie sur notre site. '
        f'Sans création de compte, un seul rappel vous sera envoyé dans {REMINDER_AFTER_DAYS} jours, puis plus rien — '
        f'<a href="{origin}/api/public/free-estimate/{token}/stop" style="color:#7b879c">ne pas recevoir ce rappel</a>.</p>'
        '</td></tr></table></td></tr></table>'
    )
    return subject, html


@router.post("")
async def send_free_estimate(payload: FreeEstimateRequest, request: Request):
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Adresse e-mail invalide.")
    if not emailer.email_ready():
        raise HTTPException(status_code=503, detail="Envoi d’e-mail indisponible pour le moment.")
    now = datetime.now(timezone.utc)
    ip = _client_ip(request)
    if await db.free_estimates.count_documents({"email": email, "created_at": {"$gte": now - timedelta(hours=24)}}) >= MAX_PER_EMAIL_24H:
        raise HTTPException(status_code=429, detail="Limite atteinte pour cette adresse e-mail (3 envois par 24 h).")
    if await db.free_estimates.count_documents({"ip": ip, "created_at": {"$gte": now - timedelta(hours=1)}}) >= MAX_PER_IP_1H:
        raise HTTPException(status_code=429, detail="Trop de demandes, réessayez dans une heure.")

    est = await run_estimation(payload.property)
    prop = PropertyDoc(**payload.property.model_dump(), estimation=est, created_at=now)
    pdf = report.build_report(prop)
    token = secrets.token_urlsafe(24)
    origin = _origin(request)
    subject, html = _email_html(origin=origin, token=token, prop=payload.property, est=est, brand=emailer.EMAIL_FROM_NAME)
    await db.free_estimates.insert_one({
        "token": token, "email": email, "ip": ip, "created_at": now, "origin": origin,
        "property": payload.property.model_dump(mode="json"), "estimation": est.model_dump(mode="json"), "pdf": pdf,
    })
    try:
        message_id = await emailer.send_email(to=email, subject=subject, html=html)
    except Exception as exc:  # adresse refusée par le service, quota… : on ne révèle rien de plus
        log.warning("free-estimate email failed for %s: %s", email, exc)
        await db.free_estimates.update_one({"token": token}, {"$set": {"email_error": str(exc)[:300]}})
        raise HTTPException(status_code=502, detail="L’e-mail n’a pas pu être envoyé. Vérifiez l’adresse et réessayez.")
    await db.free_estimates.update_one({"token": token}, {"$set": {"message_id": message_id, "sent_at": datetime.now(timezone.utc)}})
    return {"sent": True, "token": token, "pdf_url": f"{origin}/api/public/free-estimate/{token}.pdf"}


async def _find(token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,64}", token):
        raise HTTPException(status_code=404, detail="Estimation introuvable")
    doc = await db.free_estimates.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Estimation introuvable ou expirée")
    return doc


@router.get("/{token}.pdf")
async def free_estimate_pdf(token: str):
    doc = await _find(token)
    name = f"achetemamaison-estimation-{doc['created_at'].strftime('%Y%m%d')}.pdf"
    return Response(content=bytes(doc["pdf"]), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{name}"', "Cache-Control": "private, max-age=3600"})


@router.get("/{token}")
async def free_estimate_draft(token: str):
    """Reprise du bien estimé à l'inscription (`/sign-up?draft=<token>`)."""
    doc = await _find(token)
    return {"property": doc["property"], "estimation": doc["estimation"], "created_at": doc["created_at"]}


def _reminder_html(*, origin: str, token: str, prop: PropertyIn, est, brand: str) -> tuple[str, str]:
    eur = report.eur
    pdf_url = f"{origin}/api/public/free-estimate/{token}.pdf"
    signup_url = f"{origin}/sign-up?draft={token}"
    stop_url = f"{origin}/api/public/free-estimate/{token}/stop"
    subject = f"Votre estimation de {eur(est.value)} vous attend — {prop.address_label}"
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fb;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;padding:28px;'
        'font-family:Helvetica,Arial,sans-serif;color:#0f1f3d">'
        f'<tr><td><p style="margin:0 0 6px;font-size:13px;color:#1656c9;font-weight:bold;letter-spacing:1px">{escape(brand).upper()}</p>'
        f'<h1 style="margin:0 0 16px;font-size:22px">Et si vous alliez plus loin que l’estimation ?</h1>'
        f'<p style="margin:0 0 16px;font-size:14px;line-height:21px">Il y a {REMINDER_AFTER_DAYS} jours, vous avez estimé '
        f'<b>{escape(prop.address_label)}</b> à <b>{eur(est.value)}</b> (fourchette {eur(est.low)} – {eur(est.high)}).</p>'
        '<p style="margin:0 0 12px;font-size:14px;line-height:21px">Votre compte gratuit vous donne accès, en une minute :</p>'
        '<ul style="margin:0 0 20px;padding-left:20px;font-size:14px;line-height:22px">'
        '<li>au <b>dossier environnement</b> du bien : écoles, commerces, transports, nuisances, risques, urbanisme ;</li>'
        '<li>aux <b>ventes comparables</b> détaillées et à la tendance du marché local ;</li>'
        '<li>aux étapes de la vente : prix cible, photos, annonce, dossier de vente pour le notaire.</li></ul>'
        f'<p style="margin:0 0 20px"><a href="{signup_url}" style="display:inline-block;background:#1656c9;color:#ffffff;text-decoration:none;'
        'font-weight:bold;font-size:15px;padding:12px 20px;border-radius:10px">Créer mon compte gratuit</a></p>'
        f'<p style="margin:0 0 20px;font-size:14px"><a href="{pdf_url}" style="color:#1656c9">Revoir mon rapport PDF</a></p>'
        f'<p style="margin:0;font-size:11px;line-height:16px;color:#7b879c">Ceci est l’unique rappel lié à votre estimation : vous ne recevrez '
        f'aucun autre message de notre part. <a href="{stop_url}" style="color:#7b879c">Ne plus recevoir d’e-mail</a>.</p>'
        '</td></tr></table></td></tr></table>'
    )
    return subject, html


@router.get("/{token}/stop")
async def free_estimate_stop(token: str):
    """Désinscription du rappel (lien dans les e-mails) : marque toutes les estimations de cette adresse."""
    doc = await _find(token)
    await db.free_estimates.update_many({"email": doc["email"]}, {"$set": {"no_reminder": True}})
    return Response(content="<!doctype html><html lang='fr'><meta charset='utf-8'><body style='font-family:Helvetica,Arial,sans-serif;padding:40px'>"
                            "<h1 style='font-size:20px'>C’est noté</h1><p>Vous ne recevrez aucun rappel concernant votre estimation.</p></body></html>",
                    media_type="text/html")


async def send_due_reminders() -> int:
    """Rappel unique J+REMINDER_AFTER_DAYS aux visiteurs sans compte (une seule estimation par adresse e-mail est relancée)."""
    if not emailer.email_ready():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=REMINDER_AFTER_DAYS)
    cursor = db.free_estimates.find({"sent_at": {"$lte": cutoff}, "reminder_sent_at": {"$exists": False}, "reminder_skipped": {"$exists": False},
                                     "no_reminder": {"$ne": True}}, sort=[("sent_at", -1)]).limit(50)
    sent = 0
    async for doc in cursor:
        email = doc["email"]
        skip = None
        if await db.users.find_one({"email": email}):
            skip = "account_created"
        elif await db.free_estimates.find_one({"email": email, "reminder_sent_at": {"$exists": True}}):
            skip = "already_reminded"
        elif await db.free_estimates.find_one({"email": email, "sent_at": {"$gt": doc["sent_at"]}}):
            skip = "newer_estimate"
        if skip:
            await db.free_estimates.update_one({"_id": doc["_id"]}, {"$set": {"reminder_skipped": skip}})
            continue
        prop = PropertyIn(**doc["property"])
        est = _EstView(doc["estimation"])
        subject, html = _reminder_html(origin=doc["origin"], token=doc["token"], prop=prop, est=est, brand=emailer.EMAIL_FROM_NAME)
        try:
            await emailer.send_email(to=email, subject=subject, html=html)
            await db.free_estimates.update_one({"_id": doc["_id"]}, {"$set": {"reminder_sent_at": datetime.now(timezone.utc)}})
            sent += 1
        except Exception as exc:
            log.warning("free-estimate reminder failed for %s: %s", email, exc)
            await db.free_estimates.update_one({"_id": doc["_id"]}, {"$set": {"reminder_skipped": f"error: {str(exc)[:200]}"}})
    return sent


class _EstView:
    """Accès attribut sur l'estimation stockée (dict) pour les gabarits d'e-mail."""

    def __init__(self, d: dict):
        self._d = d

    def __getattr__(self, k):
        v = self._d[k]
        return _EstView(v) if isinstance(v, dict) else v


async def reminder_loop() -> None:
    await asyncio.sleep(120)
    while True:
        try:
            n = await send_due_reminders()
            if n:
                log.info("free-estimate reminders sent: %d", n)
        except Exception:
            log.exception("free-estimate reminder loop failed")
        await asyncio.sleep(REMINDER_INTERVAL_S)
