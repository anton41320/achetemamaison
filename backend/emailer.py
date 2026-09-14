"""Emails transactionnels via l'intégration Resend gérée par Emergent (reçu du Pack annonce).

Garde-fous : expéditeur = marque de l'app (EMAIL_FROM_NAME), destinataires issus des enregistrements serveur
(email client Stripe), gabarits serveur uniquement, liens https vers l'app, jamais de formulaire ni de demande
d'identifiants. `_assert_safe_email` est appelé sur chaque envoi.
"""
from __future__ import annotations

import ipaddress
import logging
import os
import re
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("emailer")

# Proxy email géré par Emergent — constante volontairement codée (survit au déploiement).
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Estimo")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


def email_ready() -> bool:
    return bool(EMAIL_KEY)


async def send_email(*, to: str, subject: str, html: str) -> str | None:
    if not EMAIL_KEY:
        raise RuntimeError("EMERGENT_EMAIL_KEY manquante")
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if EMAIL_REPLY_TO:
        payload["contact_email"] = EMAIL_REPLY_TO
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMAIL_KEY}, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def receipt_html(*, order_id: str, address_label: str, amount_cents: int, paid_at: datetime, app_origin: str,
                 property_id: str, live_mode: bool) -> tuple[str, str]:
    """(subject, html) — gabarit serveur du reçu Pack annonce premium. Liens https vers l'app uniquement."""
    brand = escape(EMAIL_FROM_NAME)
    amount = f"{amount_cents / 100:.2f}".replace(".", ",") + " €"
    date_txt = paid_at.strftime("%d/%m/%Y à %H:%M")
    origin = app_origin.rstrip("/")
    pack_url = f"{origin}/property/{property_id}/pack"
    pdf_url = f"{origin}/api/properties/{property_id}/pack.pdf"
    test_note = "" if live_mode else ('<p style="font-size:12px;color:#b45309;margin:0 0 12px">Paiement effectué en mode test Stripe : '
                                     "aucun montant réel n'a été débité.</p>")
    subject = f"Votre reçu {EMAIL_FROM_NAME} — Pack annonce premium ({amount})"
    html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f5;padding:24px 0">'
        '<tr><td align="center">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;'
        'font-family:Arial,Helvetica,sans-serif;color:#1f2a24">'
        f'<tr><td style="padding:28px 32px 8px"><p style="margin:0;font-size:20px;font-weight:bold;color:#1f5f4a">{brand}</p>'
        '<p style="margin:4px 0 0;font-size:13px;color:#6b7772">Reçu de paiement</p></td></tr>'
        f'<tr><td style="padding:16px 32px">{test_note}'
        '<p style="margin:0 0 12px;font-size:15px;line-height:22px">Merci ! Votre <strong>Pack annonce premium</strong> est débloqué pour le bien&nbsp;: '
        f'<strong>{escape(address_label)}</strong>.</p>'
        '<table role="presentation" width="100%" cellpadding="6" cellspacing="0" style="font-size:14px;border-top:1px solid #e3e8e5;border-bottom:1px solid #e3e8e5">'
        f'<tr><td style="color:#6b7772">Produit</td><td align="right">Pack annonce premium (paiement unique)</td></tr>'
        f'<tr><td style="color:#6b7772">Montant</td><td align="right"><strong>{amount}</strong> TTC</td></tr>'
        f'<tr><td style="color:#6b7772">Date</td><td align="right">{date_txt}</td></tr>'
        f'<tr><td style="color:#6b7772">N° de commande</td><td align="right">{escape(order_id)}</td></tr>'
        '</table>'
        '<p style="margin:16px 0 8px;font-size:14px;line-height:22px">Ce que vous avez débloqué&nbsp;: le PDF d’annonce (texte IA + photos retouchées), '
        'régénérable à volonté, et les retouches photo IA illimitées pour ce bien.</p>'
        f'<p style="margin:16px 0"><a href="{pdf_url}" style="display:inline-block;background:#1f5f4a;color:#ffffff;text-decoration:none;'
        'padding:12px 20px;border-radius:8px;font-weight:bold;font-size:14px">Télécharger le PDF de l’annonce</a></p>'
        f'<p style="margin:0 0 12px;font-size:13px;color:#6b7772">Ou ouvrez le pack dans l’application&nbsp;: <a href="{pack_url}" style="color:#1f5f4a">Pack annonce premium</a></p>'
        '</td></tr>'
        f'<tr><td style="padding:12px 32px 24px;font-size:12px;color:#8a948f;line-height:18px">Envoyé par {brand}. Le paiement a été traité par Stripe ; '
        'nous ne vous demanderons jamais vos identifiants ou données de carte par email.</td></tr>'
        '</table></td></tr></table>'
    )
    return subject, html
