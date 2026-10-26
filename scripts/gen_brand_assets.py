"""Génère les assets de marque (icône, splash, favicon, logo, OG image, logo PDF) à partir des fichiers de la charte."""
from pathlib import Path

from PIL import Image, ImageDraw

SRC = Path("/tmp/brand")
IMG = Path("/app/frontend/assets/images")
BACKEND = Path("/app/backend/data")
WHITE = (255, 255, 255, 255)
LIGHT = (0xE8, 0xF0, 0xFD, 255)

icon_light = Image.open(SRC / "icon-light.png").convert("RGBA")
icon_dark = Image.open(SRC / "icon-dark.png").convert("RGBA")
logo_light = Image.open(SRC / "logo-light.png").convert("RGBA")
logo_dark = Image.open(SRC / "logo-dark.png").convert("RGBA")


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    r = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)


def canvas(size, bg, art: Image.Image, scale: float, dy: float = 0.0) -> Image.Image:
    w, h = size if isinstance(size, tuple) else (size, size)
    out = Image.new("RGBA", (w, h), bg)
    a = fit(art, round(w * scale), round(h * scale))
    out.alpha_composite(a, ((w - a.width) // 2, (h - a.height) // 2 + round(h * dy)))
    return out


def rounded_tile(size: int, bg, art: Image.Image, scale: float, radius_ratio: float = 0.22) -> Image.Image:
    tile = canvas(size, bg, art, scale)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=round(size * radius_ratio), fill=255)
    tile.putalpha(mask)
    return tile


# App icon (iOS : opaque, Apple arrondit lui-même) — maison noire + plus bleu sur fond blanc
canvas(1024, WHITE, icon_light, 0.64).convert("RGB").save(IMG / "icon.png")
# Android adaptive : premier plan centré dans la zone sûre (66 %), fond blanc défini dans app.json
canvas(1024, (0, 0, 0, 0), icon_light, 0.46).save(IMG / "adaptive-icon.png")
# Monochrome Android 13+ : silhouette (alpha) de l'icône
mono = canvas(1024, (0, 0, 0, 0), icon_light, 0.46)
alpha = mono.getchannel("A")
Image.merge("RGBA", (Image.new("L", mono.size, 255),) * 3 + (alpha,)).save(IMG / "adaptive-icon-mono.png")
# Splash : logo complet sur fond blanc (image transparente, fond via app.json)
canvas(1024, (0, 0, 0, 0), logo_light, 0.78).save(IMG / "splash-image.png")
# Favicon
canvas(96, WHITE, icon_light, 0.78).convert("RGB").save(IMG / "favicon.png")
# Logo in-app : icône seule (transparent) + logo complet (transparent) + version fond sombre
canvas(512, (0, 0, 0, 0), icon_light, 1.0).save(IMG / "logo.png")
logo_light.save(IMG / "logo-wordmark.png")
logo_dark.save(IMG / "logo-wordmark-dark.png")
# OG image (1200×630) : logo sur fond clair de la charte
canvas((1200, 630), LIGHT, logo_light, 0.62).convert("RGB").save(IMG / "app-image.png")
# Backend : tuile blanche arrondie avec l'icône — en-tête PDF + signature discrète sur les photos retouchées
rounded_tile(300, WHITE, icon_light, 0.66).save(BACKEND / "logo.png")
print("ok")
