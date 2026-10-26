"""Visuels pour les fiches des stores (à téléverser manuellement) : icône Google Play 512, icône App Store 1024,
image de présentation Google Play 1024×500. Sortie : backend/store-assets.zip (servi sur /api/public/store-assets.zip)."""
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SRC = Path("/app/brand-assets")
OUT = Path("/tmp/store-assets")
OUT.mkdir(exist_ok=True)
WHITE = (255, 255, 255, 255)
LIGHT = (0xE8, 0xF0, 0xFD, 255)
INK = (0x0F, 0x1F, 0x3D)

icon = Image.open(SRC / "icon-light.png").convert("RGBA")
logo = Image.open(SRC / "logo-light.png").convert("RGBA")


def fit(im, w, h):
    r = min(w / im.width, h / im.height)
    return im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)


def canvas(size, bg, art, scale, dy=0):
    w, h = size
    out = Image.new("RGBA", (w, h), bg)
    a = fit(art, round(w * scale), round(h * scale))
    out.alpha_composite(a, ((w - a.width) // 2, (h - a.height) // 2 + dy))
    return out


canvas((512, 512), WHITE, icon, 0.64).convert("RGB").save(OUT / "google-play-icone-512.png")
canvas((1024, 1024), WHITE, icon, 0.64).convert("RGB").save(OUT / "app-store-icone-1024.png")

fg = canvas((1024, 500), LIGHT, logo, 0.55, dy=-40)
d = ImageDraw.Draw(fg)
font = ImageFont.truetype("/app/frontend/assets/fonts/PlusJakartaSans-ExtraBold.ttf", 34)
text = "De l’estimation à la vente, sans agence"
d.text(((1024 - d.textlength(text, font=font)) / 2, 370), text, fill=INK, font=font)
fg.convert("RGB").save(OUT / "google-play-image-de-presentation-1024x500.png")

with zipfile.ZipFile("/app/backend/store-assets.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        z.write(p, p.name)
print("ok")
