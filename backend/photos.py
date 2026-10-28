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

CHECK_MODEL = "gemini-3-flash-preview"

RETOUCH_PROMPT = (
    "Retouche immobilière lumineuse et naturelle : lumière du jour équilibrée, blancs neutres, ombres débouchées, couleurs fidèles, "
    "perspective corrigée, rendu réaliste sans HDR excessif. Range les pièces sans enlever ce qui est mobilier ou jolie déco.\n\n"
    "Lumière et exposition :\n"
    "- Augmenter la luminosité de manière équilibrée.\n"
    "- Corriger les zones surexposées et déboucher les ombres.\n"
    "- Rééquilibrer la lumière naturelle pour obtenir une ambiance claire et accueillante.\n"
    "- Corriger la balance des blancs pour conserver des couleurs neutres et fidèles.\n\n"
    "Perspective et géométrie :\n"
    "- Redresser les lignes verticales et horizontales.\n"
    "- Corriger la perspective et les déformations de l’objectif.\n"
    "- Conserver les proportions réelles de la pièce, le même cadrage et le même angle de vue.\n\n"
    "Couleurs et détails :\n"
    "- Améliorer subtilement le contraste, la netteté et la définition.\n"
    "- Préserver les couleurs naturelles des murs, des sols, des meubles et des matériaux.\n"
    "- Réduire le bruit numérique et améliorer la qualité générale de l’image.\n\n"
    "Mise en valeur :\n"
    "- Donner une impression d’espace, de propreté et de luminosité.\n"
    "- Valoriser les volumes, les matières et les éléments architecturaux.\n"
    "- Obtenir un style éditorial immobilier élégant, sobre et réaliste.\n\n"
    "Contraintes impératives :\n"
    "- Conserver intégralement la structure et l’apparence réelle du bien.\n"
    "- Ne modifier ni les dimensions, ni les ouvertures, ni les fenêtres, ni les portes, ni les équipements (électroménager, "
    "luminaires, radiateurs, cheminée, poutres, escaliers…).\n"
    "- Ne pas ajouter ou supprimer de meubles ni d’éléments architecturaux. « Ranger » signifie retirer, de façon invisible, le petit "
    "désordre du quotidien : aimants, papiers, photos et dessins collés sur le réfrigérateur ou les murs ; produits, bouteilles, "
    "éponges, torchons, boîtes, bols, saladiers, bocaux, ustensiles, petit électroménager portable et tout petit objet posé sur les "
    "plans de travail, tables, étagères et rebords de fenêtre (les plans de travail doivent apparaître dégagés) ; "
    "vêtements, chaussures, sacs, jouets, câbles, poubelles de table, vaisselle qui traîne ; personnes et animaux. En reconstituant "
    "exactement la surface qui se trouvait dessous (même matériau, même couleur). Le mobilier, l’électroménager, les luminaires, les "
    "rideaux, les plantes, les tableaux et la belle décoration restent à leur place, à leur taille, avec leurs matériaux et couleurs.\n"
    "- Ne pas remplacer la vue extérieure et ne pas inventer de détails.\n"
    "- En extérieur : ne pas ajouter, supprimer ni déplacer bâtiments, annexes, murs, toitures, clôtures, portails, allées, cours, "
    "terrasses, arbres, branches, haies ou pelouses ; ne pas changer la saison, la météo ni l’état de la végétation ; ne pas "
    "réparer, nettoyer ou rajeunir ce qui est abîmé (mousse, fissures, crépi, tuiles).\n"
    "- Éviter les effets HDR excessifs, les couleurs artificielles, les halos et les rendus irréalistes.\n\n"
    "Résultat attendu : une photographie immobilière professionnelle, lumineuse, équilibrée, naturelle et fidèle à la réalité, "
    "prête à être publiée sur une annonce immobilière. Un voisin qui connaît le bien doit pouvoir superposer l’original et le "
    "résultat et ne voir changer que la lumière, les couleurs et la netteté. Renvoie uniquement l’image retouchée, mêmes dimensions."
)

STRICT_SUFFIX = (
    "\n\nATTENTION — une première tentative a trop modifié la photo ({issues}). Recommence en te limitant strictement à "
    "exposition, couleurs et netteté : aucune modification de contenu, même minime."
)

CHECK_PROMPT = (
    "Image 1 = photo originale d'un bien immobilier, image 2 = version retouchée. La retouche ne devait modifier que la lumière, "
    "les couleurs, la netteté et une légère correction de perspective. Compare les deux images et vérifie si des éléments ont été "
    "ajoutés, supprimés, déplacés ou redessinés (arbres, branches, végétation, bâtiments, annexes, murs, toits, fenêtres, portes, "
    "clôtures, allées, cours, sols, mobilier, objets de décoration, équipements : électroménager, luminaires, radiateurs, poutres, "
    "véhicules), si des matériaux ou couleurs de murs/sols/meubles ont changé, si la vue par les fenêtres a été remplacée, "
    "si la saison/météo/état de la végétation a changé, ou si des défauts "
    "réels ont été effacés. Le retrait de personnes, d’animaux et du petit désordre (aimants/papiers sur le frigo, produits et objets "
    "sur les plans de travail et tables, vêtements, vaisselle, câbles) est voulu et accepté : ne le signale pas. Ignore les "
    "différences de luminosité, de couleur globale, de contraste, de netteté et les petits décalages de "
    "cadrage. Réponds UNIQUEMENT en JSON : {\"faithful\": true|false, \"issues\": [\"…\"]} — issues en français, vide si fidèle."
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


class UnfaithfulRetouch(RuntimeError):
    """La retouche a modifié le contenu de la photo (éléments ajoutés/supprimés) : on garde l'original."""


async def _generate(image_bytes: bytes, prompt: str) -> bytes:
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage  # lazy: keeps LLM SDKs out of startup memory

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"retouch-{uuid.uuid4()}",
                   system_message="You are a professional real-estate photo editor. You only do photographic post-processing; "
                                  "you never add, remove, move or redraw any element of the scene.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    msg = UserMessage(text=prompt, file_contents=[ImageContent(base64.b64encode(image_bytes).decode("utf-8"))])
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError("Le modèle n'a renvoyé aucune image")
    return base64.b64decode(images[0]["data"])


async def check_fidelity(original: bytes, edited: bytes) -> tuple[bool, list[str]]:
    """Second regard (modèle vision texte) : la retouche a-t-elle ajouté / supprimé / redessiné des éléments ?"""
    import json
    import re

    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"retouch-check-{uuid.uuid4()}",
                   system_message="Tu compares deux photos et réponds uniquement en JSON.").with_model("gemini", CHECK_MODEL)
    msg = UserMessage(text=CHECK_PROMPT, file_contents=[
        ImageContent(base64.b64encode(original).decode("utf-8")), ImageContent(base64.b64encode(edited).decode("utf-8"))])
    text = await chat.send_message(msg)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return True, []  # vérification indisponible : on ne bloque pas
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return True, []
    issues = [str(i) for i in (data.get("issues") or [])][:5]
    return bool(data.get("faithful", True)), issues


async def retouch(image_bytes: bytes) -> tuple[bytes, str]:
    """Retouche + contrôle de fidélité ; une seconde tentative plus stricte si la première a modifié le contenu."""
    raw = await _generate(image_bytes, RETOUCH_PROMPT)
    ok, issues = await check_fidelity(image_bytes, raw)
    if not ok:
        raw = await _generate(image_bytes, RETOUCH_PROMPT + STRICT_SUFFIX.format(issues="; ".join(issues) or "contenu modifié"))
        ok, issues = await check_fidelity(image_bytes, raw)
        if not ok:
            raise UnfaithfulRetouch("La retouche IA modifiait la photo (" + "; ".join(issues)[:160] + "). L’original est conservé.")
    return normalize(raw)
