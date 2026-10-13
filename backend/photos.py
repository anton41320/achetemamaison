"""Phase 5 — AI photo retouching (Gemini Nano Banana) with strict "no added elements" guardrail."""
from __future__ import annotations

import base64
import io
import os
import uuid
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

try:  # HEIC / HEIF / AVIF (photos iPhone partagées, certains Android)
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:  # noqa: BLE001
    pass

MODEL = "gemini-3.1-flash-image-preview"
MAX_SIDE = 1600

RETOUCH_PROMPT = (
    "Transforme cette photo immobilière en une photographie professionnelle haut de gamme destinée à une annonce immobilière.\n\n"
    "Objectif : mettre en valeur le bien pour séduire les acheteurs potentiels, tout en conservant un rendu réaliste et fidèle à la propriété.\n\n"
    "Style photographique : photographie immobilière professionnelle, lumière naturelle douce, exposition équilibrée, couleurs neutres "
    "et élégantes, blancs lumineux, détails nets, perspective corrigée, lignes verticales droites, grand-angle maîtrisé, profondeur et "
    "sensation d'espace.\n\n"
    "Retouches souhaitées :\n"
    "- Optimiser la luminosité et le contraste sans surexposer.\n"
    "- Valoriser les volumes, les matériaux et les détails architecturaux.\n"
    "- Ranger la pièce en laissant les éléments attachés aux murs ; enlever les personnes et les photos de personnes ; éclaircir les zones d'ombre.\n"
    "- Rééquilibrer la balance des blancs pour obtenir des couleurs naturelles.\n"
    "- Corriger les perspectives et les déformations optiques.\n"
    "- Réduire le bruit numérique et améliorer la netteté.\n"
    "- Donner une impression de propreté, de fraîcheur et de bien-être.\n"
    "- Pour une photo extérieure, valoriser le ciel, la lumière et les espaces verts de manière naturelle.\n"
    "- Pour une photo intérieure, créer une ambiance chaleureuse, lumineuse et accueillante.\n\n"
    "Contraintes essentielles : conserver fidèlement l'architecture, les dimensions, les ouvertures, les équipements, les matériaux et "
    "l'agencement existants. Ne pas ajouter de fenêtres, de pièces, de mobilier ou d'éléments inexistants. Ne pas masquer les défauts "
    "réels ni modifier les caractéristiques du bien. Conserver le même angle de prise de vue et le même cadrage.\n\n"
    "Résultat attendu : une photographie photoréaliste, élégante, lumineuse et crédible, digne d'une annonce immobilière professionnelle, "
    "adaptée aux portails immobiliers et aux supports de communication d'une agence. Renvoie uniquement l'image retouchée."
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


LOGO_PATH = Path(__file__).parent / "data" / "logo.png"


def watermark(data: bytes) -> tuple[bytes, str]:
    """Discreet brand signature: rounded logo, ~9 % of the shortest side, bottom-right, 80 % opacity, soft shadow."""
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    w, h = img.size
    size = max(56, int(min(w, h) * 0.09))
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((size, size), Image.LANCZOS)
    alpha = logo.getchannel("A").point(lambda a: int(a * 0.8))
    logo.putalpha(alpha)
    margin = max(12, int(min(w, h) * 0.025))
    x, y = w - size - margin, h - size - margin
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", (size, size), (0, 0, 0, 90)), (x + 2, y + 3), logo.getchannel("A"))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    img = Image.alpha_composite(img, shadow)
    img.paste(logo, (x, y), logo)
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=90, optimize=True)
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
