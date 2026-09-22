"""Compose App Store marketing screenshots (caption + framed capture) from raw Playwright captures."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path("/app/store-assets")
FONT_DIR = Path("/app/frontend/assets/fonts")
BOLD = str(FONT_DIR / "PlusJakartaSans-Bold.ttf")
REGULAR = str(FONT_DIR / "PlusJakartaSans-Regular.ttf")
TOP = (22, 86, 201)
BOTTOM = (11, 59, 143)

CAPTIONS = {
    "01-welcome": ("Estimez, préparez, vendez", "L’app qui accompagne le vendeur de l’estimation jusqu’au notaire"),
    "02-home": ("Tous vos biens en un coup d’œil", "Fourchette de prix, niveau de confiance et prochaine étape"),
    "03-property": ("Une estimation fondée sur les ventes réelles", "Données DVF officielles, confiance expliquée critère par critère"),
    "04-comparables": ("Comprenez chaque euro", "Ventes comparables : distance, surface, prix au m²"),
    "05-dossier": ("Un dossier de vente prêt pour le notaire", "Checklist des diagnostics, rappels d’expiration, export PDF"),
    "06-pack": ("Outils IA : annonce, photos, documents", "Pack premium 49 € par bien, sans abonnement"),
    "07-photos": ("Photos retouchées par l’IA", "Lumière et perspective améliorées, rien n’est inventé"),
}


def gradient(w: int, h: int) -> Image.Image:
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        base.putpixel((0, y), tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)))
    return base.resize((w, h))


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def compose(raw: Path, out: Path, size: tuple[int, int], scale: float, title_px: int, sub_px: int, radius: int) -> None:
    W, H = size
    canvas = gradient(W, H)
    draw = ImageDraw.Draw(canvas)
    f_title = ImageFont.truetype(BOLD, title_px)
    f_sub = ImageFont.truetype(REGULAR, sub_px)
    title, sub = CAPTIONS[raw.stem]
    y = int(H * 0.055)
    for line in wrap(draw, title, f_title, W - 160):
        tw = draw.textlength(line, font=f_title)
        draw.text(((W - tw) / 2, y), line, font=f_title, fill=(255, 255, 255))
        y += int(title_px * 1.15)
    y += int(sub_px * 0.4)
    for line in wrap(draw, sub, f_sub, W - 200):
        tw = draw.textlength(line, font=f_sub)
        draw.text(((W - tw) / 2, y), line, font=f_sub, fill=(214, 228, 250))
        y += int(sub_px * 1.35)

    shot = Image.open(raw).convert("RGB")
    sw, sh = int(shot.width * scale), int(shot.height * scale)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, sh - 1), radius=radius, fill=255)
    x0 = (W - sw) // 2
    y0 = y + int(sub_px * 1.6)
    # soft shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x0 + 10, y0 + 30, x0 + sw - 10, y0 + sh + 30), radius=radius, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(40))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow)
    # device bezel
    bezel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bezel).rounded_rectangle((x0 - 14, y0 - 14, x0 + sw + 13, y0 + sh + 13), radius=radius + 14, fill=(10, 24, 56, 255))
    canvas = Image.alpha_composite(canvas, bezel)
    canvas.paste(shot, (x0, y0), mask)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print(out.name, canvas.size)


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "iphone"
    if kind == "iphone":
        raw_dir, out_dir, size = ROOT / "raw", ROOT / "iphone-6.9", (1320, 2868)
        params = dict(scale=0.86, title_px=84, sub_px=44, radius=96)
    elif kind == "iphone65":
        raw_dir, out_dir, size = ROOT / "raw", ROOT / "iphone-6.5", (1284, 2778)
        params = dict(scale=0.836, title_px=82, sub_px=43, radius=94)
    else:
        raw_dir, out_dir, size = ROOT / "raw-ipad", ROOT / "ipad-13", (2064, 2752)
        params = dict(scale=0.84, title_px=96, sub_px=50, radius=72)
    out_dir.mkdir(parents=True, exist_ok=True)
    for raw in sorted(raw_dir.glob("*.png")):
        compose(raw, out_dir / f"{raw.stem}.png", size, **params)
