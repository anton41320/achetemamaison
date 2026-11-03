"""Portrait du « fondateur » (fictif) pour la page Facebook / le site : homme ~50 ans, présentable mais authentique, rendu photo smartphone.
Sortie : frontend/assets/images/fondateur-{1,2}.jpg. Usage : python scripts/gen_founder_portrait.py
⚠️ Personne fictive : à remplacer par une vraie photo du fondateur avant usage comme « visage » de la marque.
"""
import asyncio
import base64
import io
import os

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

load_dotenv("/app/backend/.env")
OUT = "/app/frontend/assets/images"
MODEL = "gemini-3.1-flash-image-preview"

BASE = ("Photo authentique, prise avec un smartphone récent par un proche, pas un portrait de studio : aucun look publicitaire, "
        "aucune retouche, peau naturelle avec rides d'expression, pores visibles, quelques cheveux gris mal coiffés, légère asymétrie du visage. "
        "Lumière naturelle de fin d'après-midi, légèrement dure, petites ombres sous les yeux. Grain léger, couleurs réalistes un peu ternes. "
        "Cadrage légèrement imparfait, horizon pas tout à fait droit. Aucun texte, aucun logo, aucun filigrane. Format 4:5 vertical. ")
SCENES = {
    "fondateur-1": BASE + "Sujet : un homme français d'une cinquantaine d'années, cheveux poivre et sel courts, barbe de trois jours grisonnante, "
    "lunettes fines, chemise bleu clair col ouvert légèrement froissée, manches retroussées, veste en laine marine posée sur l'épaule. Il est debout "
    "devant le portail d'un pavillon de province, un trousseau de clés dans une main et son téléphone dans l'autre, sourire discret et franc, "
    "regard vers l'objectif. Arrière-plan : haie, voiture grise un peu poussiéreuse, boîte aux lettres.",
    "fondateur-2": BASE + "Sujet : le même homme d'une cinquantaine d'années, cheveux poivre et sel courts, barbe de trois jours, lunettes fines, "
    "pull col rond gris anthracite sur chemise blanche, assis à une table de cuisine en bois encombrée (tasse de café, dossier bleu ouvert, "
    "ordinateur portable fermé), en train d'expliquer quelque chose avec la main, mi-sourire naturel, regard vers l'objectif. Lumière de fenêtre "
    "latérale, fond légèrement flou avec frigo couvert d'aimants et de papiers.",
}


def naturalize(im: Image.Image) -> Image.Image:
    im = ImageEnhance.Contrast(im).enhance(0.96)
    im = ImageEnhance.Color(im).enhance(0.9)
    noise = Image.effect_noise(im.size, 12).convert("L")
    im = Image.blend(im, Image.merge("RGB", (noise, noise, noise)), 0.05)
    vign = Image.new("L", im.size, 0)
    ImageDraw.Draw(vign).ellipse((-im.width * 0.2, -im.height * 0.25, im.width * 1.2, im.height * 1.25), fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(200))
    im = Image.composite(im, Image.blend(im, Image.new("RGB", im.size, (20, 18, 24)), 0.22), vign)
    return Image.blend(im, Image.new("RGB", im.size, (255, 214, 170)), 0.03)


async def gen(name: str) -> None:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"founder-{name}", system_message="Tu es un photographe.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    text, images = await chat.send_message_multimodal_response(UserMessage(text=SCENES[name]))
    if not images:
        raise SystemExit(f"{name}: aucune image ; {(text or '')[:200]}")
    im = Image.open(io.BytesIO(base64.b64decode(images[0]["data"]))).convert("RGB")
    if im.width > 1200:
        im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
    naturalize(im).save(f"{OUT}/{name}.jpg", quality=88, optimize=True)
    print(name, "->", im.size)


async def main():
    for n in SCENES:
        await gen(n)


if __name__ == "__main__":
    asyncio.run(main())
