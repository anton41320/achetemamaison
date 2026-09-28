"""« Signaler un problème » : retours des testeurs (écran, commentaire, capture, appareil, compte) → base + e-mail au propriétaire."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from html import escape
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

import auth
import emailer
import photos as photo_ai
import storage
from models import utcnow

logger = logging.getLogger("feedback")
router = APIRouter()
_db = None


def init(db) -> None:
    global _db
    _db = db


def feedback_to() -> str:
    return (os.environ.get("FEEDBACK_TO_EMAIL") or "").strip()


def _html(*, user_email: str, screen: str, platform: str, app_version: str, message: str, screenshot_url: Optional[str], created: str) -> str:
    rows = [("Compte", user_email), ("Écran", screen or "—"), ("Appareil", platform or "—"), ("Version de l’app", app_version or "—"), ("Date", created)]
    table = "".join(f"<tr><td style='padding:6px 12px 6px 0;color:#6B7C99;white-space:nowrap'>{escape(k)}</td><td style='padding:6px 0'>{escape(v)}</td></tr>" for k, v in rows)
    shot = (f"<p><a href='{escape(screenshot_url)}' style='color:#1D4ED8'>Voir la capture d’écran jointe</a></p>"
            f"<p><img src='{escape(screenshot_url)}' alt='Capture d’écran' style='max-width:360px;border:1px solid #DCE5F2;border-radius:12px'></p>") if screenshot_url else ""
    return (f"<div style='font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0F1F3D;line-height:1.5'>"
            f"<h2 style='margin:0 0 12px'>Nouveau signalement testeur</h2><table style='border-collapse:collapse;font-size:14px'>{table}</table>"
            f"<h3 style='margin:18px 0 6px'>Commentaire</h3><p style='white-space:pre-wrap;background:#F4F7FC;padding:12px;border-radius:12px'>{escape(message)}</p>{shot}</div>")


@router.post("/feedback")
async def send_feedback(request: Request, message: str = Form(min_length=3, max_length=2000), screen: str = Form(default=""),
                        platform: str = Form(default=""), app_version: str = Form(default=""), file: UploadFile | None = File(default=None)):
    user = auth.current_user_var.get() or {}
    screenshot_path = None
    if file is not None:
        raw = await file.read()
        if len(raw) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Capture trop lourde (15 Mo max)")
        try:
            data, mime = await asyncio.to_thread(photo_ai.normalize, raw)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="Capture illisible (image attendue)")
        screenshot_path = f"{storage.APP_NAME}/feedback/{uuid.uuid4()}.jpg"
        try:
            await asyncio.to_thread(storage.put_object, screenshot_path, data, mime)
        except storage.StorageError as exc:
            logger.warning("feedback screenshot upload failed: %s", exc)
            screenshot_path = None
    created = utcnow()
    doc = {"user_id": str(user.get("_id", "")), "user_email": user.get("email", ""), "message": message.strip(), "screen": screen[:200],
           "platform": platform[:120], "app_version": app_version[:40], "screenshot_path": screenshot_path, "created_at": created, "emailed": False}
    res = await _db.feedback.insert_one(doc)

    to = feedback_to()
    emailed = False
    if to and emailer.email_ready():
        origin = str(request.base_url).rstrip("/").replace("http://", "https://")
        shot_url = f"{origin}/api/files/{screenshot_path}" if screenshot_path else None
        try:
            await emailer.send_email(to=to, subject=f"[Signalement] {screen or 'app'} — {doc['user_email'] or 'testeur'}",
                                     html=_html(user_email=doc["user_email"] or "—", screen=screen, platform=platform, app_version=app_version,
                                                message=doc["message"], screenshot_url=shot_url, created=created.strftime("%d/%m/%Y %H:%M UTC")))
            emailed = True
            await _db.feedback.update_one({"_id": res.inserted_id}, {"$set": {"emailed": True}})
        except Exception:  # noqa: BLE001
            logger.exception("feedback email failed")
    return {"ok": True, "id": str(res.inserted_id), "emailed": emailed}
