"""Visuels de conversion Pack premium (3 cartes 1200×900). Illustrations Gemini (clé Emergent) sans texte,
typographie Plus Jakarta Sans ajoutée par Pillow (texte net, sans faute). Sortie : frontend/assets/images/premium-{1,2,3}.jpg
Usage : python scripts/gen_premium_visuals.py [--no-gen]  (--no-gen réutilise les illustrations déjà générées dans /tmp/premium-src)
"""
import asyncio
import base64
import os
import sys

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFilter, ImageFont

load_dotenv("/app/backend/.env")
SRC = "/tmp/premium-src"
OUT = "/app/frontend/assets/images"
FONTS = "/app/frontend/assets/fonts"
MODEL = "gemini-3.1-flash-image-preview"
W, H = 1200, 900
BRAND, BRAND_DEEP, SOFT, INK, MUTED, WHITE, GREEN = "#1656C9", "#0B3B8F", "#E8F0FD", "#0F1B2D", "#5B6B82", "#FFFFFF", "#1E9E6A"

STYLE = (
    "Illustration éditoriale haut de gamme pour une application immobilière française moderne. Palette : bleu profond #1656C9 et #0B3B8F, "
    "blanc, touches de vert tendre et de beige chaud. Style flat vectoriel légèrement texturé, lumière douce, très propre, "
    "SANS AUCUN TEXTE, sans lettres, sans chiffres, sans logo, sans filigrane. Fond uni très clair (#F3F6FB). Format 4:3, sujet centré "
    "occupant les deux tiers supérieurs, le tiers inférieur reste vide et uni."
)
PROMPTS = {
    "annonce": STYLE + " Sujet : un smartphone tenu de face affichant une annonce immobilière stylisée (photo de maison en haut, "
    "blocs de lignes grises symbolisant le texte, une étiquette de prix vide), entouré de petites étincelles bleues et d'une plume "
    "stylisée symbolisant la rédaction automatique. À côté, deux ou trois pictogrammes de quartier reliés par des pointillés : école, "
    "arbre de parc, train.",
    "dossier": STYLE + " Sujet : une chemise cartonnée bleue ouverte d'où dépassent plusieurs documents stylisés (feuilles blanches avec "
    "blocs de lignes grises), chacun marqué d'une grande coche verte dans un cercle. Au premier plan un tampon rond stylisé et un stylo plume. "
    "En arrière-plan discret, la silhouette d'une maison et d'une clé.",
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


async def gen(name: str) -> None:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"premium-visual-{name}", system_message="Tu es un illustrateur.")
    chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
    text, images = await chat.send_message_multimodal_response(UserMessage(text=PROMPTS[name]))
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


def rounded(im: Image.Image, r: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width, im.height), r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def pill(draw: ImageDraw.ImageDraw, xy, text: str, f, bg, fg, pad=(22, 12)):
    x, y = xy
    tw = draw.textlength(text, font=f)
    th = f.size
    draw.rounded_rectangle((x, y, x + tw + 2 * pad[0], y + th + 2 * pad[1]), (th + 2 * pad[1]) // 2, fill=bg)
    draw.text((x + pad[0], y + pad[1] - 2), text, font=f, fill=fg)
    return x + tw + 2 * pad[0]


def card(illustration: Image.Image, kicker: str, title: str, subtitle: str, bullets: list[str], out: str, crop=None) -> None:
    bg = illustration.getpixel((4, 4)) if crop else (243, 246, 251)
    base = Image.new("RGB", (W, H), bg)
    if crop:
        sub = illustration.crop(crop)
        s = min(W / sub.width, 450 / sub.height)
        sub = sub.resize((round(sub.width * s), round(sub.height * s)), Image.LANCZOS)
        base.paste(sub, ((W - sub.width) // 2, 30))
    else:
        base.paste(cover(illustration, W, 560), (0, 0))
    # dégradé de fusion vers le bas
    grad = Image.new("L", (1, 200))
    for i in range(200):
        grad.putpixel((0, i), int(255 * i / 199))
    grad = grad.resize((W, 200))
    base.paste(Image.new("RGB", (W, 200), bg), (0, 380), grad)
    d = ImageDraw.Draw(base)
    pill(d, (56, 36), kicker, font("Bold", 24), BRAND, WHITE)
    d.text((56, 470), title, font=font("ExtraBold", 58), fill=INK)
    d.text((56, 548), subtitle, font=font("Medium", 28), fill=MUTED)
    y = 620
    for b in bullets:
        d.ellipse((56, y + 6, 56 + 26, y + 32), fill=GREEN)
        d.line((63, y + 19, 68, y + 25, 76, y + 13), fill=WHITE, width=3)
        d.text((98, y), b, font=font("SemiBold", 27), fill=INK)
        y += 48
    # bandeau prix
    d.rounded_rectangle((56, H - 120, W - 56, H - 48), 20, fill=BRAND_DEEP)
    d.text((84, H - 102), "Pack premium", font=font("ExtraBold", 30), fill=WHITE)
    d.text((W - 84 - d.textlength("49 € une fois · 0 % de commission", font=font("SemiBold", 28)), H - 100),
           "49 € une fois · 0 % de commission", font=font("SemiBold", 28), fill="#CFE0FF")
    base.save(out, quality=90, optimize=True)
    print("->", out)


def photos_card(out: str) -> None:
    before = Image.open(f"{OUT}/demo-before.jpg").convert("RGB")
    after = Image.open(f"{OUT}/demo-after.jpg").convert("RGB")
    canvas = Image.new("RGB", (W, 560), "#F3F6FB")
    half = (W - 56 * 2 - 24) // 2
    b, a = rounded(cover(before, half, 420), 28), rounded(cover(after, half, 420), 28)
    shadow = Image.new("RGBA", (half + 40, 460), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((20, 24, half + 20, 444), 28, fill=(11, 59, 143, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    for x, im in ((56, b), (56 + half + 24, a)):
        canvas.paste(shadow, (x - 20, 60), shadow)
        canvas.paste(im, (x, 70), im)
    d = ImageDraw.Draw(canvas)
    pill(d, (56 + 20, 90), "AVANT", font("Bold", 22), "#0F1B2D", WHITE, (18, 9))
    pill(d, (56 + half + 24 + 20, 90), "APRÈS · retouche IA", font("Bold", 22), BRAND, WHITE, (18, 9))
    # flèche centrale
    cx = 56 + half + 12
    d.ellipse((cx - 34, 250, cx + 34, 318), fill=WHITE, outline=BRAND, width=4)
    d.polygon([(cx - 10, 268), (cx + 12, 284), (cx - 10, 300)], fill=BRAND)
    card(canvas, "ÉTAPE 2 · MISE EN VENTE", "Des photos qui donnent envie", "Retouche IA : rangé, lumineux, et toujours fidèle à votre bien.",
         ["Désencombrement et lumière corrigés automatiquement", "Rien n'est ajouté : l'acheteur voit le vrai bien", "Originaux conservés, export HD en un clic"], out)


async def main():
    if "--no-gen" not in sys.argv:
        for n in PROMPTS:
            await gen(n)
    photos_card(f"{OUT}/premium-1.jpg")
    card(Image.open(f"{SRC}/annonce.png").convert("RGB"), "ÉTAPE 2 · MISE EN VENTE", "Votre annonce rédigée en 10 secondes",
         "Un texte professionnel, prêt à copier sur Leboncoin, SeLoger ou PAP.",
         ["Accroche et description adaptées à votre bien", "Atouts du quartier mesurés : écoles, gare, commerces", "Prix de vente affiché exactement comme vous le fixez"],
         f"{OUT}/premium-2.jpg", crop=(300, 100, 960, 600))
    card(Image.open(f"{SRC}/dossier.png").convert("RGB"), "ÉTAPE 2 · DOSSIER DE VENTE", "Le dossier complet, prêt pour le notaire",
         "La liste exacte des documents obligatoires pour votre bien.",
         ["Checklist adaptée : maison, appartement, copropriété", "Vos diagnostics lus et vérifiés automatiquement", "PDF de vente complet à remettre aux acheteurs"],
         f"{OUT}/premium-3.jpg", crop=(60, 150, 1140, 640))


asyncio.run(main())
