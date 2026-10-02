"""Pack annonce premium (49 €) — Stripe Checkout (one-off) + entitlement per property + premium listing PDF."""
from __future__ import annotations

import logging
import os
from datetime import date
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse

import stripe
from fastapi import HTTPException
from bson import ObjectId
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import auth
import emailer
from models import PropertyDoc, utcnow
from report import APP_NAME, BRAND, BRAND_SOFT, CONDITION_LABELS, INK, LINE, MUTED, eur

logger = logging.getLogger("pack")

PACK_PRICE_CENTS = 4900
PACK_CURRENCY = "eur"
PACK_NAME = f"Pack annonce premium {APP_NAME}"
FREE_RETOUCHES = 0  # aucune retouche offerte : tous les outils IA exigent le pack


def stripe_ready() -> bool:
    key = os.environ.get("STRIPE_API_KEY")
    if key:
        stripe.api_key = key
        if "sk_test_emergent" in key:
            # Emergent-managed test key: route through the integrations proxy (same as emergentintegrations).
            stripe.api_base = os.environ.get("INTEGRATION_PROXY_URL", "https://integrations.emergentagent.com").rstrip("/") + "/stripe"
        else:
            stripe.api_base = "https://api.stripe.com"
    return bool(key)


def live_mode() -> bool:
    return (os.environ.get("STRIPE_API_KEY") or "").startswith("sk_live_")


def payments_config() -> dict:
    return {"payments_available": stripe_ready(), "mode": "live" if live_mode() else "test",
            "webhook_configured": bool(os.environ.get("STRIPE_WEBHOOK_SECRET")), "email_ready": emailer.email_ready()}


async def _mark_paid(db, order: dict, session) -> None:
    details = session.get("customer_details") or {}
    res = await db.orders.update_one({"_id": order["_id"], "status": {"$ne": "paid"}},
                                     {"$set": {"status": "paid", "paid_at": utcnow(), "payment_intent": session.get("payment_intent"),
                                               "customer_email": details.get("email"), "customer_name": details.get("name"),
                                               "amount_total": session.get("amount_total"), "live_mode": bool(session.get("livemode"))}})
    if res.modified_count:
        await send_receipt(db, await db.orders.find_one({"_id": order["_id"]}))


async def send_receipt(db, order: dict) -> bool:
    """Send the receipt once per paid order (recipient = Stripe checkout email, a server-side record)."""
    to = order.get("customer_email")
    if not to or order.get("receipt_sent_at") or not emailer.email_ready():
        return False
    prop = await db.properties.find_one({"_id": ObjectId(order["property_id"])}, {"address_label": 1})
    origin = urlparse(order.get("return_url") or "")
    app_origin = f"{origin.scheme}://{origin.netloc}" if origin.scheme == "https" and origin.netloc else None
    if not app_origin or not prop:
        logger.warning("Receipt skipped for order %s: missing https origin or property", order["_id"])
        return False
    subject, html = emailer.receipt_html(order_id=str(order["_id"]), address_label=prop["address_label"],
                                         amount_cents=order.get("amount_total") or order["amount"], paid_at=order.get("paid_at") or utcnow(),
                                         app_origin=app_origin, property_id=order["property_id"], live_mode=bool(order.get("live_mode")))
    try:
        email_id = await emailer.send_email(to=to, subject=subject, html=html)
    except Exception:  # noqa: BLE001
        logger.exception("Receipt email failed for order %s", order["_id"])
        await db.orders.update_one({"_id": order["_id"]}, {"$set": {"receipt_error": "send_failed"}})
        return False
    await db.orders.update_one({"_id": order["_id"]}, {"$set": {"receipt_sent_at": utcnow(), "receipt_email_id": email_id}, "$unset": {"receipt_error": ""}})
    return True


def comp_emails() -> set[str]:
    """Comptes « invités » (testeurs, proches) : le pack est offert sur tous leurs biens. PREMIUM_COMP_EMAILS=a@x.fr,b@y.fr"""
    return {e.strip().lower() for e in os.environ.get("PREMIUM_COMP_EMAILS", "").split(",") if e.strip()}


async def is_unlocked(db, pid: str) -> bool:
    if await db.orders.find_one({"property_id": pid, "status": "paid"}, {"_id": 1}) is not None:
        return True
    user = auth.current_user_var.get()
    if user and user.get("promo_code"):  # code promo testeur : tout le compte
        return True
    return bool(user) and (user.get("email") or "").lower() in comp_emails()


PAYWALL_DETAIL = "Pack annonce premium requis (49 €)"


async def require_unlocked(db, pid: str, feature: str) -> None:
    """Every AI tool (annonce, retouche photo, lecture OCR) is reserved to the premium pack of the property."""
    if not await is_unlocked(db, pid):
        raise HTTPException(status_code=402, detail=f"{PAYWALL_DETAIL} : {feature} est réservée aux biens ayant débloqué le pack.")


async def create_checkout(db, pid: str, return_url: str, owner_id: Optional[str] = None) -> dict:
    if not stripe_ready():
        raise RuntimeError("Paiement indisponible : clé Stripe absente")
    order_id = str(ObjectId())
    sep = "&" if "?" in return_url else "?"
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price_data": {"currency": PACK_CURRENCY, "unit_amount": PACK_PRICE_CENTS,
                                    "product_data": {"name": PACK_NAME,
                                                     "description": "Outils IA débloqués pour ce bien : annonce, retouches photo illimitées, lecture des documents, PDF premium",
                                                     # Service fourni par voie électronique (requis par Stripe Managed Payments)
                                                     "tax_code": "txcd_10000000"}},
                     "quantity": 1}],
        success_url=f"{return_url}{sep}status=success&order_id={order_id}",
        cancel_url=f"{return_url}{sep}status=cancelled&order_id={order_id}",
        metadata={"order_id": order_id, "property_id": pid},
    )
    await db.orders.insert_one({"_id": ObjectId(order_id), "property_id": pid, "amount": PACK_PRICE_CENTS, "currency": PACK_CURRENCY,
                                "status": "pending", "return_url": return_url, "session_id": session.id, "owner_id": owner_id, "created_at": utcnow()})
    return {"order_id": order_id, "checkout_url": session.url}


async def sync_pending(db, pid: str) -> None:
    """Polling fallback: ask Stripe about pending sessions (server-side, verified) when no webhook is configured."""
    if not stripe_ready():
        return
    async for o in db.orders.find({"property_id": pid, "status": "pending", "session_id": {"$ne": None}}):
        try:
            s = stripe.checkout.Session.retrieve(o["session_id"])
        except Exception:  # noqa: BLE001
            logger.exception("Stripe retrieve failed")
            continue
        if s.get("payment_status") == "paid":
            await _mark_paid(db, o, s)
        elif s.get("status") == "expired":
            await db.orders.update_one({"_id": o["_id"]}, {"$set": {"status": "failed"}})
    # Retry receipts that failed earlier (e.g. email service hiccup)
    async for o in db.orders.find({"property_id": pid, "status": "paid", "receipt_sent_at": None, "customer_email": {"$ne": None}}):
        await send_receipt(db, o)


async def handle_webhook(db, payload: bytes, signature: Optional[str]) -> dict:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret or not signature:
        raise ValueError("Webhook non configuré")
    event = stripe.Webhook.construct_event(payload, signature, secret)
    try:
        await db.webhook_events.insert_one({"_id": event["id"], "received_at": utcnow()})
    except Exception:  # noqa: BLE001 — duplicate delivery
        return {"received": True, "duplicate": True}
    session = event["data"]["object"]
    order_id = (session.get("metadata") or {}).get("order_id")
    if not order_id:
        return {"received": True}
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        return {"received": True}
    if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded") and session.get("payment_status") == "paid":
        await _mark_paid(db, order, session)
    elif event["type"] in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        await db.orders.update_one({"_id": order["_id"], "status": "pending"}, {"$set": {"status": "failed"}})
    return {"received": True}


# ---------------- Premium PDF ----------------

def build_pack_pdf(prop: PropertyDoc, listing: dict, photos: list[tuple[bytes, bool]], final: Optional[dict],
                   target: Optional[dict], include_price: bool) -> bytes:
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=MUTED)
    title = ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=BRAND, alignment=0)
    hook = ParagraphStyle("hook", parent=body, fontName="Helvetica-Oblique", fontSize=12, leading=17, textColor=BRAND)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=INK, spaceBefore=8, spaceAfter=4)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"{listing['title']} — {APP_NAME}")
    story = []
    max_w, max_h = A4[0] - 32 * mm, A4[1] - 28 * mm

    def fitted(data: bytes, h_cap: float) -> Image:
        im = PILImage.open(BytesIO(data))
        w, h = im.size
        scale = min(max_w / w, h_cap / h)
        return Image(BytesIO(data), width=w * scale, height=h * scale)

    # Cover: hero photo + title + hook
    if photos:
        story.append(fitted(photos[0][0], 120 * mm))
        story.append(Spacer(1, 6))
    story.append(Paragraph(listing["title"], title))
    ptype = "Maison" if prop.property_type == "maison" else "Appartement"
    meta = f"{ptype} · {prop.surface:g} m² · {prop.rooms} pièces · {prop.bedrooms} chambre(s) · {prop.commune} ({prop.postcode})"
    if prop.property_type == "maison" and prop.land_surface:
        meta += f" · terrain {prop.land_surface:g} m²"
    story.append(Paragraph(meta, small))
    story.append(Spacer(1, 6))
    story.append(Paragraph(listing["hook"], hook))
    if include_price and final:
        story.append(Spacer(1, 6))
        price_txt = f"<b>Prix : {eur(target['target_price'])}</b>" if target else f"<b>Fourchette de valeur estimée : {eur(final['low'])} – {eur(final['high'])}</b>"
        t = Table([[Paragraph(price_txt, body)]], colWidths=[max_w])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                               ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
        story.append(t)
    story.append(PageBreak())

    # Description + highlights
    story.append(Paragraph("Description", h2))
    for para in listing["description"].split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body))
            story.append(Spacer(1, 4))
    if listing.get("highlights"):
        story.append(Paragraph("Points forts", h2))
        for hl in listing["highlights"]:
            story.append(Paragraph(f"• {hl}", body))
    story.append(Paragraph("Caractéristiques", h2))
    rows = [["Type", ptype], ["Surface habitable", f"{prop.surface:g} m²"], ["Pièces / chambres", f"{prop.rooms} / {prop.bedrooms}"],
            ["État déclaré", CONDITION_LABELS.get(prop.condition, prop.condition)]]
    if prop.year_built:
        rows.append(["Année de construction", str(prop.year_built)])
    if prop.property_type == "maison" and prop.land_surface:
        rows.append(["Terrain", f"{prop.land_surface:g} m²"])
    f = prop.features
    if f.dpe:
        rows.append(["DPE", f.dpe])
    if f.heating:
        rows.append(["Chauffage", f.heating.replace("_", " ")])
    if f.fireplace and f.fireplace != "aucune":
        from listing import FIREPLACE_LABELS

        rows.append(["Cheminée / poêle", FIREPLACE_LABELS[f.fireplace]])
    if f.pool and f.pool != "aucune":
        rows.append(["Piscine", f.pool.replace("_", " ")])
    if f.garage and f.garage != "aucun":
        rows.append(["Garage", "oui" if f.garage == "un" else "double ou plus"])
    if prop.property_type == "appartement":
        if f.floor is not None:
            rows.append(["Étage", ("Rez-de-chaussée" if f.floor == 0 else f"{f.floor}e") + ("" if f.elevator is None else (" · avec ascenseur" if f.elevator else " · sans ascenseur"))])
        if f.parking and f.parking != "aucun":
            rows.append(["Parking", "intérieur / box" if f.parking == "interieur" else "extérieur"])
        if f.caretaker:
            rows.append(["Gardien", "oui"])
        if f.condo_fees is not None:
            rows.append(["Charges de copropriété", f"{f.condo_fees:g} €/mois"])
        if f.heating_mode or f.underfloor_heating:
            rows.append(["Mode de chauffage", ", ".join(x for x in (f.heating_mode, "au sol" if f.underfloor_heating else None) if x)])
    t = Table([[Paragraph(a, body), Paragraph(b, body)] for a, b in rows], colWidths=[60 * mm, max_w - 60 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t)

    # Photo pages
    for i, (data, retouched) in enumerate(photos[1:], 2):
        story.append(PageBreak())
        story.append(fitted(data, max_h - 20 * mm))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Photo {i}/{len(photos)}" + (" · visuel retouché par IA, non contractuel" if retouched else ""), small))

    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Annonce générée avec {APP_NAME} le {date.today().strftime('%d/%m/%Y')} à partir des informations déclarées par le vendeur. "
                           "Les visuels retouchés par IA (luminosité, netteté, couleurs) n'ajoutent aucun élément et restent non contractuels. "
                           "Diagnostics et surfaces à confirmer dans le dossier de vente.", small))
    doc.build(story)
    return buf.getvalue()
