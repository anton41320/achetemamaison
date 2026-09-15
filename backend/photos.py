"""Phase 5 — AI photo retouching (Gemini Nano Banana) with strict "no added elements" guardrail."""
from __future__ import annotations

import base64
import io
import os
import uuid

from PIL import Image, ImageOps

MODEL = "gemini-3.1-flash-image-preview"
MAX_SIDE = 1600

RETOUCH_PROMPT = (
    "Tu es un retoucheur de photos immobilières professionnel. Retouche cette photo en respectant STRICTEMENT les règles :\n"
    "- Améliore l'exposition, la luminosité, la balance des blancs, le contraste et la netteté de façon naturelle.\n"
    "- Redresse les verticales (perspective) si elles sont penchées, sans déformer la pièce.\n"
    "- Désencombrement léger uniquement : tu peux effacer de petits objets temporaires (papiers, câbles, poubelle, chaussures).\n"
    "- INTERDIT : ajouter un élément qui n'existe pas (meuble, décoration, fenêtre, plante, vue, ciel différent), "
    "modifier la structure, les matériaux, les couleurs des murs/sols, la taille des pièces ou la vue extérieure.\n"
    "- Conserve exactement le même cadrage et le même contenu. Le résultat doit rester une représentation fidèle du bien.\n"
    "Renvoie uniquement l'image retouchée."
)


def normalize(data: bytes) -> tuple[bytes, str]:
    """Re-encode as JPEG, EXIF-rotated, max 1600 px on the longest side (cost + privacy: strips metadata)."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue(), "image/jpeg"


async def retouch(image_bytes: bytes) -> tuple[bytes, str]:
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage  # lazy: keeps LLM SDKs out of startup memory

    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(api_key=api_key, session_id=f"retouch-{uuid.uuid4()}",
                   system_message="You are a professional real-estate photo editor.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    msg = UserMessage(text=RETOUCH_PROMPT, file_contents=[ImageContent(base64.b64encode(image_bytes).decode("utf-8"))])
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError("Le modèle n'a renvoyé aucune image")
    raw = base64.b64decode(images[0]["data"])
    return normalize(raw)
