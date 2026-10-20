"""Génération ponctuelle des visuels de la page d'accueil web (Gemini image, clé Emergent). Sortie : frontend/assets/web/*.png"""
import asyncio
import base64
import os
import sys

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")
OUT = "/app/frontend/assets/web"
MODEL = "gemini-3.1-flash-image-preview"

STYLE = (
    "Illustration éditoriale haut de gamme pour un site immobilier français moderne. Palette : bleu profond #1656C9 et #0B3B8F, "
    "blanc cassé, touches de vert tendre et de beige chaud. Style flat vectoriel légèrement texturé, lumière douce de fin de journée, "
    "très propre, sans texte, sans lettres, sans logo, sans filigrane, fond uni clair (#F3F6FB) en dehors du sujet. Format 16:10."
)

PROMPTS = {
    "hero-house": STYLE + " Sujet : une jolie maison individuelle française (pierre claire et tuiles, volets bleus, grande baie vitrée) "
    "sur une parcelle arborée, vue en légère perspective trois-quarts, avec au premier plan une étiquette de prix stylisée (sans chiffres, "
    "juste une forme) et une petite loupe flottante symbolisant l'estimation. Ambiance rassurante et optimiste, composition centrée.",
    "map-data": STYLE + " Sujet : une carte stylisée vue de dessus en perspective isométrique d'un quartier avec, au centre, la maison "
    "estimée mise en évidence par un halo bleu. Autour, des pictogrammes reliés par de fines lignes à la maison : une école, des commerces, "
    "une gare / arrêt de transport, un parc avec arbres, une route avec une icône de bruit, une vague d'eau pour le risque d'inondation, "
    "une courbe de relief. Dispersées sur la carte, plusieurs petites maisons voisines marquées d'une coche verte et d'une étiquette de prix "
    "vide, symbolisant les ventes réelles récentes utilisées comme références. Les lignes convergent vers une jauge / fourchette de prix "
    "stylisée au-dessus de la maison. Pas de texte, pas de chiffres, pas de lettres.",
}


async def gen(name: str, prompt: str) -> None:
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"web-visual-{name}", system_message="Tu es un illustrateur.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if not images:
        print(name, "-> aucune image ;", (text or "")[:200])
        return
    data = base64.b64decode(images[0]["data"])
    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/{name}.png"
    with open(path, "wb") as f:
        f.write(data)
    print(name, "->", path, len(data) // 1024, "Ko", images[0]["mime_type"])


async def main():
    names = sys.argv[1:] or list(PROMPTS)
    for n in names:
        await gen(n, PROMPTS[n])


asyncio.run(main())
