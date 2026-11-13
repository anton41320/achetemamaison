"""Bannières LinkedIn basées sur le nouveau héros du site (calques assets/hero/d-*.webp).
Sorties : backend/media/linkedin-profil.png (1584×396, photo de profil en bas à gauche) et linkedin-page.png (1128×191, page entreprise).
Usage : python scripts/gen_linkedin_banner.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT = "/app/backend/media"
BRAND, SECOND, TERTIARY, WHITE, INK = (22, 86, 201), (127, 163, 227), (232, 240, 253), (255, 255, 255), (15, 27, 45)


def font(name, size):
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def layer(name, w):
    im = Image.open(f"{ASSETS}/hero/{name}.webp").convert("RGBA")
    return im.resize((w, round(w * im.height / im.width)), Image.LANCZOS)


def banner(W, H, profile_safe):
    """profile_safe : largeur réservée à gauche (photo de profil LinkedIn)."""
    im = Image.new("RGB", (W, H), TERTIARY)
    d = ImageDraw.Draw(im)
    k = H / 396  # échelle par rapport à la bannière profil
    # aplat bleu arrondi (comme le site), de la zone texte jusqu'à Noisette
    x0 = int(profile_safe + 40 * k)
    x1 = int(W * 0.68)
    d.rounded_rectangle((x0, -int(140 * k), x1, H + int(140 * k)), radius=int(170 * k), fill=BRAND)
    # forme logo en haut de l'aplat
    ls = layer("d-logo-shape", int(190 * k))
    im.paste(ls, (x0 + int(30 * k), -int(60 * k)), ls)
    # textes
    tx = x0 + int(60 * k)
    f1, f2, f3 = font("ExtraBold", int(38 * k)), font("Medium", int(19 * k)), font("Bold", int(19 * k))
    d.text((tx, int(86 * k)), "Prêt à connaître", font=f1, fill=WHITE)
    d.text((tx, int(132 * k)), "la valeur de votre bien ?", font=f1, fill=WHITE)
    d.text((tx, int(204 * k)), "Estimation gratuite en 2 minutes, à partir des ventes réelles.", font=f2, fill=WHITE)
    d.text((tx, int(232 * k)), "Puis vendez sans agence, sans commission.", font=f2, fill=WHITE)
    bw, bh = int(250 * k), int(48 * k)
    d.rounded_rectangle((tx, int(290 * k), tx + bw, int(290 * k) + bh), radius=int(10 * k), fill=WHITE)
    s = "achetemamaison.fr"
    d.text((tx + (bw - d.textlength(s, font=f3)) / 2, int(290 * k) + (bh - f3.size) / 2 - int(2 * k)), s, font=f3, fill=BRAND)
    # Noisette + plus, à droite
    ph = int(380 * k)
    plus = layer("d-plus", ph)
    noi = layer("d-noisette", int(292 * k))
    px0 = x1 - int(30 * k)
    im.paste(plus, (px0, (H - plus.height) // 2 + int(20 * k)), plus)
    im.paste(noi, (px0 + int(14 * k), (H - noi.height) // 2 + int(24 * k)), noi)
    # 3 étapes à droite
    sx = px0 + plus.width - int(40 * k)
    if sx + int(250 * k) < W:
        for i, lab in enumerate(("Estimation", "Mise en vente", "Vendu")):
            yy = int((70 + i * 95) * k)
            d.ellipse((sx, yy, sx + int(36 * k), yy + int(36 * k)), fill=BRAND)
            fnum = font("Bold", int(18 * k))
            d.text((sx + int(18 * k) - d.textlength(str(i + 1), font=fnum) / 2, yy + int(7 * k)), str(i + 1), font=fnum, fill=WHITE)
            d.text((sx + int(50 * k), yy + int(4 * k)), lab, font=font("Bold", int(22 * k)), fill=INK)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    banner(1584, 396, 400).save(f"{OUT}/linkedin-profil.png", optimize=True)
    banner(1128, 191, 60).save(f"{OUT}/linkedin-page.png", optimize=True)
    print("->", f"{OUT}/linkedin-profil.png", f"{OUT}/linkedin-page.png")


if __name__ == "__main__":
    main()
