"""Notifications administrateur via un bot Telegram (sortant uniquement).

Variables : TELEGRAM_BOT_TOKEN (BotFather) et TELEGRAM_CHAT_ID (conversation du gérant avec le bot).
Sans ces variables, les appels sont ignorés silencieusement. Envoi en tâche de fond : jamais bloquant,
jamais d'erreur remontée vers l'utilisateur.
"""
from __future__ import annotations

import asyncio
import logging
import os
from html import escape

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("telegram")

API = "https://api.telegram.org"


def _config() -> tuple[str, str] | None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return (token, chat) if token and chat else None


def ready() -> bool:
    return _config() is not None


async def send(text: str) -> bool:
    cfg = _config()
    if not cfg:
        return False
    token, chat = cfg
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{API}/bot{token}/sendMessage",
                                  json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
        if r.status_code != 200:
            logger.warning("Telegram sendMessage %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Telegram unreachable: %s", e)
        return False


def notify(text: str) -> None:
    """Fire-and-forget depuis un contexte async."""
    if ready():
        asyncio.get_running_loop().create_task(send(text))


def new_user(email: str, total_users: int | None = None) -> None:
    tail = f"\n👥 Total : <b>{total_users}</b> comptes" if total_users is not None else ""
    notify(f"🆕 <b>Nouvelle inscription</b>\n✉️ {escape(email)}{tail}")


def premium_purchase(provider: str, email: str | None, address: str | None, amount_cents: int | None, currency: str | None,
                     environment: str | None = None) -> None:
    amount = f"{(amount_cents or 0) / 100:.2f} {(currency or 'eur').upper()}"
    lines = ["💰 <b>Pack premium acheté</b>", f"🏷️ {escape(provider)}" + (f" · {escape(environment)}" if environment else "")]
    if email:
        lines.append(f"✉️ {escape(email)}")
    if address:
        lines.append(f"🏠 {escape(address)}")
    lines.append(f"💶 {amount}")
    notify("\n".join(lines))
