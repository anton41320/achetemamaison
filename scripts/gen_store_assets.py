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

fg = Image.new("RGBA", (1024, 500), LIGHT)
lg = fit(logo, 520, 150)
fg.alpha_composite(lg, (70, 95))
noisette = Image.open("/app/frontend/assets/mascot/noisette-pouce.webp").convert("RGBA")
noisette = fit(noisette, 400, 400)
fg.alpha_composite(noisette, (1024 - noisette.width - 40, 500 - noisette.height - 30))
d = ImageDraw.Draw(fg)
font = ImageFont.truetype("/app/frontend/assets/fonts/PlusJakartaSans-ExtraBold.ttf", 40)
sub = ImageFont.truetype("/app/frontend/assets/fonts/PlusJakartaSans-Medium.ttf", 26)
d.text((70, 285), "Vendez vous-même,", fill=INK, font=font)
d.text((70, 335), "mais pas tout seul.", fill=INK, font=font)
d.text((70, 405), "Estimation gratuite en 2 minutes · sans agence", fill=(0x5B, 0x6B, 0x82), font=sub)
fg.convert("RGB").save(OUT / "google-play-image-de-presentation-1024x500.png")

with zipfile.ZipFile("/app/backend/store-assets.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        z.write(p, p.name)
print("ok")
