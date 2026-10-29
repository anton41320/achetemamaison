"""Visuels témoignages « ils ont vendu avec nous » (3 cartes 1200×900). Photos photoréalistes Gemini (clé Emergent),
citation + prénom + ville + mention « photo d'illustration » ajoutés par Pillow. Sortie : frontend/assets/images/temoignage-{1,2,3}.jpg
Usage : python scripts/gen_testimonial_visuals.py [--no-gen]
⚠️ Personnes et témoignages fictifs : à remplacer par de vrais clients (avec accord écrit) avant toute diffusion publicitaire.
"""
import asyncio
import base64
import os
import sys

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv("/app/backend/.env")
SRC = "/tmp/temoignage-src"
OUT = "/app/frontend/assets/images"
FONTS = "/app/frontend/assets/fonts"
MODEL = "gemini-3.1-flash-image-preview"
W, H = 1200, 900
BRAND, GREEN, WHITE = "#1656C9", "#1E9E6A", "#FFFFFF"

STYLE = (
    "Photo authentique prise au smartphone par un proche, façon album de famille : pas de look publicitaire, pas de retouche, "
    "cadrage légèrement imparfait, lumière naturelle parfois un peu dure, grain léger, couleurs réalistes. Personnes françaises "
    "ordinaires, visages naturels (rides, cernes, cheveux un peu décoiffés), vêtements du quotidien (jean, polaire, baskets). "
    "Arrière-plan réel et un peu encombré : voiture garée, poubelle, tuyau d'arrosage, vélo, boîte aux lettres. Cadrage horizontal 4:3, "
    "sujets dans la moitié gauche ou au centre, le bas de l'image reste simple (sol, allée, pelouse). Aucun texte ni lettre nulle part, "
    "sauf une feuille A4 blanche avec le mot « VENDU » écrit à la main au feutre bleu. Aucun logo, aucun filigrane."
)
SCENES = {
    "couple-maison": STYLE + " Scène : un couple d'une quarantaine d'années devant leur pavillon des années 80 en crépi beige avec volets "
    "roulants, portail gris, haie de thuyas. La femme tient la feuille A4 « VENDU » à deux mains, l'homme a les clés à la main et "
    "un bras autour de ses épaules ; ils rient, un peu éblouis par le soleil.",
    "senior-appartement": STYLE + " Scène : une femme d'environ 65 ans, cheveux gris, lunettes, gilet beige, debout sur le palier de son "
    "appartement devant sa porte d'entrée ouverte, des cartons de déménagement fermés derrière elle. Elle tient la feuille A4 « VENDU » "
    "contre elle et sourit, un peu émue. Photo prise dans la cage d'escalier avec lumière de fenêtre.",
    "famille-moderne": STYLE + " Scène : un couple de trentenaires avec une petite fille de 5 ans, devant une maison de lotissement "
    "récente en enduit blanc, garage, pelouse avec trampoline au fond, voiture familiale garée sur l'allée. La petite fille brandit la "
    "feuille A4 « VENDU » au-dessus de sa tête, les parents rient derrière elle. Photo légèrement en contre-plongée, prise par un voisin.",
}
CARDS = [
    ("couple-maison", "« Vendu en 5 semaines, au prix estimé, sans agence. »", "Sophie & Marc · Blois (41)", "≈ 11 500 € de commission économisés"),
    ("senior-appartement", "« Le dossier pour le notaire était prêt avant la première visite. »", "Martine, 64 ans · Tours (37)", "Vente signée en 7 semaines"),
    ("famille-moderne", "« 9 visites dès la première semaine grâce à l'annonce et aux photos IA. »", "Julien & Camille · Orléans (45)", "Vendu 4 000 € au-dessus de l'estimation basse"),
]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


async def gen(name: str) -> None:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"temoignage-{name}", system_message="Tu es un photographe.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    text, images = await chat.send_message_multimodal_response(UserMessage(text=SCENES[name]))
    if not images:
        raise SystemExit(f"{name}: aucune image ; {(text or '')[:200]}")
    os.makedirs(SRC, exist_ok=True)
    with open(f"{SRC}/{name}.png", "wb") as f:
        f.write(base64.b64decode(images[0]["data"]))
    print(name, "généré")


def cover(im: Image.Image, w: int, h: int) -> Image.Image:
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    return lines + [cur]


def pill(draw, xy, text, f, bg, fg, pad=(20, 11)):
    x, y = xy
    tw = draw.textlength(text, font=f)
    draw.rounded_rectangle((x, y, x + tw + 2 * pad[0], y + f.size + 2 * pad[1]), (f.size + 2 * pad[1]) // 2, fill=bg)
    draw.text((x + pad[0], y + pad[1] - 2), text, font=f, fill=fg)
    return x + tw + 2 * pad[0]


def naturalize(im: Image.Image) -> Image.Image:
    """Grain fin, vignette douce et léger voile chaud pour casser le rendu trop lisse."""
    import random

    from PIL import ImageEnhance

    im = ImageEnhance.Contrast(im).enhance(0.96)
    im = ImageEnhance.Color(im).enhance(0.92)
    noise = Image.effect_noise(im.size, 14).convert("L")
    grain = Image.merge("RGB", (noise, noise, noise))
    im = Image.blend(im, grain, 0.06)
    vign = Image.new("L", im.size, 0)
    ImageDraw.Draw(vign).ellipse((-im.width * 0.25, -im.height * 0.35, im.width * 1.25, im.height * 1.35), fill=255)
    vign = vign.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(220))
    dark = Image.new("RGB", im.size, (20, 18, 24))
    im = Image.composite(im, Image.blend(im, dark, 0.28), vign)
    warm = Image.new("RGB", im.size, (255, 214, 170))
    return Image.blend(im, warm, 0.035)


def card(src: str, quote: str, who: str, result: str, out: str) -> None:
    base = naturalize(cover(Image.open(src).convert("RGB"), W, H))
    # voile sombre progressif en bas pour la lisibilité
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(460):
        a = int(215 * (i / 459) ** 1.4)
        od.line((0, H - 460 + i, W, H - 460 + i), fill=(8, 20, 45, a))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(base)
    pill(d, (48, 40), "ILS ONT VENDU AVEC ACHÈTE MA MAISON", font("Bold", 22), BRAND, WHITE)
    fq = font("ExtraBold", 46)
    lines = wrap(d, quote, fq, W - 96)
    y = H - 150 - 56 - len(lines) * 56
    for ln in lines:
        d.text((48, y), ln, font=fq, fill=WHITE)
        y += 56
    d.text((48, y + 10), who, font=font("SemiBold", 28), fill="#CFE0FF")
    x_end = pill(d, (48, H - 118), result, font("Bold", 24), GREEN, WHITE)
    pill(d, (x_end + 14, H - 118), "Pack premium · 49 € une fois", font("Bold", 24), WHITE, BRAND)
    d.text((W - 48 - d.textlength("Photo d'illustration", font=font("Medium", 18)), H - 34), "Photo d'illustration",
           font=font("Medium", 18), fill="#9FB3D1")
    base.save(out, quality=90, optimize=True)
    print("->", out)


async def main():
    if "--no-gen" not in sys.argv:
        for n in SCENES:
            await gen(n)
    for i, (name, quote, who, result) in enumerate(CARDS, 1):
        card(f"{SRC}/{name}.png", quote, who, result, f"{OUT}/temoignage-{i}.jpg")


asyncio.run(main())
