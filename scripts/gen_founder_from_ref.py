"""Portrait « fondateur » inspiré d'une photo de référence (allure, âge, coiffure, barbe, tenue) mais avec un visage DIFFÉRENT,
non reconnaissable, rendu photo smartphone authentique. Sortie : frontend/assets/images/fondateur-5.jpg, fondateur-6.jpg
Usage : python scripts/gen_founder_from_ref.py /chemin/reference.jpg
"""
import asyncio
import base64
import io
import os
import sys

from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from gen_founder_portrait import naturalize  # noqa: E402

load_dotenv("/app/backend/.env")
OUT = "/app/frontend/assets/images"
MODEL = "gemini-3.1-flash-image-preview"

PROMPT = (
    "Tu reçois une photo de référence en noir et blanc. Ne garde que l'ESPRIT : homme d'environ 45 ans, soigné mais naturel, regard posé et "
    "confiant, prestance tranquille. Tout le reste doit être DIFFÉRENT pour qu'il soit impossible de le reconnaître : cheveux châtain clair "
    "grisonnants aux tempes, courts et un peu en bataille (PAS coiffés en arrière), barbe de trois jours clairsemée (PAS de barbe taillée), "
    "visage plus rond et plus large, nez plus marqué, yeux clairs, sourcils plus fins, quelques taches de rousseur. Tenue différente : "
    "polo ou chemise unie bleu marine ou verte, PAS de rayures, PAS de logo brodé. "
    "Rendu : photo COULEUR authentique prise au smartphone par un proche, pas un portrait studio : lumière naturelle de fin d'après-midi, "
    "peau naturelle avec pores et quelques rides, cheveux légèrement décoiffés par le vent, chemise un peu froissée, grain léger, couleurs "
    "réalistes un peu ternes, cadrage légèrement imparfait. Aucun texte, aucun logo, aucun filigrane. Format 4:5 vertical. "
)
SCENES = {
    "fondateur-5": PROMPT + "Scène : debout devant le portail d'un pavillon de province, un trousseau de clés dans la main, sourire discret ; "
    "arrière-plan : haie, boîte aux lettres, voiture un peu poussiéreuse.",
    "fondateur-6": PROMPT + "Scène : assis à une table de cuisine en bois encombrée (tasse de café, dossier bleu ouvert, téléphone), en train "
    "d'expliquer quelque chose de la main, mi-sourire naturel ; lumière de fenêtre latérale, fond flou avec frigo couvert d'aimants.",
}


async def gen(name: str, ref_b64: str) -> None:
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"founder-ref-{name}", system_message="Tu es un photographe.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    text, images = await chat.send_message_multimodal_response(UserMessage(text=SCENES[name], file_contents=[ImageContent(image_base64=ref_b64)]))
    if not images:
        raise SystemExit(f"{name}: aucune image ; {(text or '')[:200]}")
    im = Image.open(io.BytesIO(base64.b64decode(images[0]["data"]))).convert("RGB")
    if im.width > 1200:
        im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
    naturalize(im).save(f"{OUT}/{name}.jpg", quality=88, optimize=True)
    print(name, "->", im.size)


async def main():
    ref = Image.open(sys.argv[1]).convert("RGB")
    ref.thumbnail((1024, 1024))
    buf = io.BytesIO()
    ref.save(buf, "JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    for n in SCENES:
        await gen(n, b64)


asyncio.run(main())
