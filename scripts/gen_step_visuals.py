"""Visuels des pages « étapes » du site (/etape-estimation, /etape-mise-en-vente, /etape-vendu).
Illustrations et photos authentiques Gemini (clé Emergent) SANS texte ; mockup téléphone Pillow. Sortie : frontend/assets/web/step-*.jpg
Usage : python scripts/gen_step_visuals.py [--only nom ...]
"""
import asyncio
import base64
import io
import os
import sys

from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from gen_social_visuals import gradient, phone, shadow_paste  # noqa: E402

load_dotenv("/app/backend/.env")
OUT = "/app/frontend/assets/web"
MODEL = "gemini-3.1-flash-image-preview"

ILLU = ("Illustration éditoriale haut de gamme pour une application immobilière française. Palette : bleu profond #1656C9 et #0B3B8F, "
        "blanc, touches de vert tendre et beige chaud. Style flat vectoriel légèrement texturé, lumière douce, très propre. "
        "SANS AUCUN TEXTE, sans lettres, sans chiffres, sans logo. Fond uni très clair #F3F6FB. Format 3:2. ")
PHOTO = ("Photo authentique prise au smartphone par un proche, façon album de famille : aucun look publicitaire, aucune retouche, cadrage "
         "légèrement imparfait, lumière naturelle, grain léger, couleurs réalistes. Personnes françaises ordinaires, visages naturels, "
         "vêtements du quotidien. Arrière-plan réel et un peu encombré. Format 3:2. Aucun texte, aucune lettre, aucun panneau, aucun logo. ")

SCENES = {
    "step1-sources": ILLU + "Sujet : une maison de village française vue de trois quarts posée sur une carte stylisée ; autour d'elle, des "
    "épingles de localisation et de petits pictogrammes reliés par des pointillés : une balance, un graphique en courbe ascendante, une "
    "règle d'arpenteur, un soleil, un arbre, une école, un train. Une loupe survole la maison.",
    "step1-trust": ILLU + "Sujet : trois jauges circulaires stylisées (sans chiffres) alignées, remplies à des niveaux différents, posées "
    "devant une rangée de maisons mitoyennes stylisées de hauteurs variées ; une coche verte dans un bouclier au premier plan.",
    "step2-annonce": ILLU + "Sujet : un smartphone de face affichant une annonce immobilière stylisée (photo de maison en haut, blocs de "
    "lignes grises symbolisant le texte, une étiquette de prix vide), entouré d'étincelles bleues et d'une plume stylisée. À côté, trois "
    "pictogrammes de quartier reliés par des pointillés : école, arbre, train.",
    "step2-visite": ILLU + "Sujet : une porte d'entrée de maison ouverte, lumineuse, avec un paillasson, une plante en pot et une paire de "
    "clés tendue au premier plan par une main stylisée ; un calendrier stylisé sans chiffres accroché à côté.",
    "step3-dossier": ILLU + "Sujet : une chemise cartonnée bleue ouverte d'où dépassent plusieurs documents stylisés (feuilles blanches à "
    "blocs de lignes grises), chacun marqué d'une grande coche verte dans un cercle ; un tampon rond et un stylo plume au premier plan ; "
    "silhouette discrète d'une maison et d'une clé en arrière-plan.",
    "step3-notaire": PHOTO + "Scène : dans le bureau d'un notaire de province (bibliothèque de codes rouges et verts, bureau en bois "
    "encombré de dossiers, fenêtre à rideaux), un vendeur d'une cinquantaine d'années en chemise un peu froissée tend un trousseau de "
    "clés à un jeune couple d'acheteurs assis en face ; tout le monde sourit ; le notaire en costume gris est flou au second plan.",
    "step3-couple": PHOTO + "Scène : un couple d'une quarantaine d'années devant leur pavillon des années 80 en crépi beige, volets "
    "roulants, portail gris, haie de thuyas ; l'homme tient les clés, la femme a un carton de déménagement dans les bras ; ils rient, "
    "un peu éblouis par le soleil ; voiture poussiéreuse garée dans l'allée.",
    "step3-famille": PHOTO + "Scène : un couple de trentenaires avec une petite fille de 5 ans sur les épaules du père, devant une maison "
    "de lotissement récente en enduit blanc avec garage, pelouse avec trampoline au fond ; la mère tient un dossier bleu sous le bras ; "
    "photo légèrement en contre-plongée prise par un voisin.",
}


async def gen(name: str) -> None:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"step-visual-{name}", system_message="Tu es un illustrateur-photographe.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    text, images = await chat.send_message_multimodal_response(UserMessage(text=SCENES[name]))
    if not images:
        raise SystemExit(f"{name}: aucune image ; {(text or '')[:200]}")
    im = Image.open(io.BytesIO(base64.b64decode(images[0]["data"]))).convert("RGB")
    if im.width > 1400:
        im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
    im.save(f"{OUT}/{name}.jpg", quality=86, optimize=True)
    print(name, "->", im.size)


def phone_visual() -> None:
    """Mockup de l'écran d'estimation sur fond dégradé marque (3:2)."""
    W, H = 1200, 800
    im = gradient(W, H)
    ph = phone(330)
    shadow_paste(im, ph, ((W - ph.width) // 2, 70), blur=40, offset=(0, 30), alpha=130)
    im = im.crop((0, 0, W, H))
    im.save(f"{OUT}/step1-phone.jpg", quality=88, optimize=True)
    print("step1-phone ->", im.size)


async def main():
    only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None
    if only is None or "step1-phone" in only:
        phone_visual()
    for n in SCENES:
        if only is None or n in only:
            await gen(n)


asyncio.run(main())
