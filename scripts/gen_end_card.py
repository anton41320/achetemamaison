"""Visuel de fin de vidéo : logo, accroche, site, badges App Store / Google Play, Noisette.
Sorties : backend/media/fin-video-{vertical,carre,paysage}.png
Usage : python scripts/gen_end_card.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT = "/app/backend/media"
DEEP, BRAND, WHITE, PALE, INK = (11, 59, 143), (22, 86, 201), (255, 255, 255), (207, 224, 255), (15, 27, 45)


def font(name, size):
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def gradient(w, h):
    im = Image.new("RGB", (w, h), DEEP)
    px = im.load()
    for y in range(h):
        k = y / h
        c = tuple(int(DEEP[i] + (BRAND[i] - DEEP[i]) * k) for i in range(3))
        for x in range(w):
            px[x, y] = c
    # halo doux derrière la mascotte
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((w * 0.15, h * 0.55, w * 0.85, h * 1.05), fill=(90, 150, 255, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    im.paste(glow, (0, 0), glow)
    return im


def text_center(d, cx, y, s, f, fill):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill)


def apple_logo(d, x, y, s, fill=WHITE):
    """Pomme stylisée : corps = 2 cercles, morsure, feuille."""
    r = s * 0.34
    d.ellipse((x, y + s * 0.3, x + 2 * r, y + s * 0.3 + 2 * r), fill=fill)
    d.ellipse((x + s * 0.3, y + s * 0.3, x + s * 0.3 + 2 * r, y + s * 0.3 + 2 * r), fill=fill)
    d.rectangle((x + r * 0.6, y + s * 0.55, x + s * 0.3 + r * 1.4, y + s * 0.3 + 2 * r), fill=fill)
    d.ellipse((x + s * 0.72, y + s * 0.36, x + s * 0.72 + s * 0.46, y + s * 0.36 + s * 0.46), fill=None)
    # morsure (couleur du fond)
    d.ellipse((x + s * 0.78, y + s * 0.42, x + s * 1.1, y + s * 0.74), fill=(0, 0, 0))
    # feuille
    d.polygon([(x + s * 0.5, y + s * 0.3), (x + s * 0.62, y + s * 0.02), (x + s * 0.82, y + s * 0.1), (x + s * 0.58, y + s * 0.3)], fill=fill)


def play_logo(d, x, y, s):
    """Triangle Google Play en 4 couleurs."""
    cx, cy = x + s * 0.5, y + s * 0.5
    pts = {"tl": (x + s * 0.08, y), "bl": (x + s * 0.08, y + s), "r": (x + s * 0.98, cy), "mid_top": (x + s * 0.7, y + s * 0.33), "mid_bot": (x + s * 0.7, y + s * 0.67)}
    d.polygon([pts["tl"], pts["bl"], (cx, cy)], fill=(0, 212, 255))      # bleu
    d.polygon([pts["tl"], (cx, cy), pts["mid_top"]], fill=(0, 240, 118))  # vert
    d.polygon([pts["bl"], (cx, cy), pts["mid_bot"]], fill=(255, 61, 0))   # rouge
    d.polygon([pts["mid_top"], pts["r"], pts["mid_bot"], (cx, cy)], fill=(255, 206, 0))  # jaune


def badge(im, x, y, w, h, kind):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x, y, x + w, y + h), radius=h * 0.22, fill=(0, 0, 0), outline=(120, 140, 170), width=2)
    s = h * 0.5
    if kind == "ios":
        apple_logo(d, x + h * 0.28, y + h * 0.22, s)
        small, big = "Télécharger dans", "l’App Store"
    else:
        play_logo(d, x + h * 0.3, y + h * 0.25, s)
        small, big = "Disponible sur", "Google Play"
    tx = x + h * 0.28 + s + h * 0.28
    d.text((tx, y + h * 0.2), small, font=font("Medium", int(h * 0.2)), fill=WHITE)
    d.text((tx, y + h * 0.44), big, font=font("Bold", int(h * 0.36)), fill=WHITE)


def paste_alpha(im, src, xy, alpha=1.0):
    if alpha < 1:
        src = src.copy()
        src.putalpha(src.getchannel("A").point(lambda v: int(v * alpha)))
    im.paste(src, xy, src)


def render(w, h, layout):
    im = gradient(w, h)
    d = ImageDraw.Draw(im)
    logo = Image.open(f"{ASSETS}/images/logo-wordmark-dark.png").convert("RGBA")
    mascot = Image.open(f"{ASSETS}/mascot/noisette-pouce.webp").convert("RGBA")
    if layout == "vertical":  # 1080×1920
        lw = 560
        logo = logo.resize((lw, round(lw * logo.height / logo.width)))
        paste_alpha(im, logo, ((w - lw) // 2, 230))
        f = font("ExtraBold", 82)
        text_center(d, w / 2, 470, "Estimez votre bien", f, WHITE)
        text_center(d, w / 2, 570, "gratuitement, en 2 min.", f, WHITE)
        text_center(d, w / 2, 690, "Puis vendez sans agence, sans commission.", font("SemiBold", 36), PALE)
        d.rounded_rectangle((170, 800, w - 170, 930), radius=65, fill=WHITE)
        text_center(d, w / 2, 832, "achetemamaison.fr", font("Bold", 56), BRAND)
        bw, bh, gap = 390, 120, 24
        bx = (w - (2 * bw + gap)) // 2
        badge(im, bx, 990, bw, bh, "ios")
        badge(im, bx + bw + gap, 990, bw, bh, "android")
        m = mascot.resize((640, 640))
        paste_alpha(im, m, ((w - 640) // 2, 1150))
        text_center(d, w / 2, 1830, "Noisette vous accompagne de l’estimation à la vente", font("Medium", 30), PALE)
    elif layout == "carre":  # 1080×1080
        lw = 440
        logo = logo.resize((lw, round(lw * logo.height / logo.width)))
        paste_alpha(im, logo, (90, 90))
        f = font("ExtraBold", 62)
        d.text((90, 230), "Estimez votre bien", font=f, fill=WHITE)
        d.text((90, 305), "gratuitement, en 2 min.", font=f, fill=WHITE)
        d.text((90, 400), "Sans agence, sans commission.", font=font("SemiBold", 30), fill=PALE)
        d.rounded_rectangle((90, 480, 640, 580), radius=50, fill=WHITE)
        text_center(d, 365, 505, "achetemamaison.fr", font("Bold", 44), BRAND)
        badge(im, 90, 640, 340, 104, "ios")
        badge(im, 90, 770, 340, 104, "android")
        m = mascot.resize((540, 540))
        paste_alpha(im, m, (w - 540 - 10, h - 540 - 10))
    else:  # paysage 1920×1080
        lw = 520
        logo = logo.resize((lw, round(lw * logo.height / logo.width)))
        paste_alpha(im, logo, (140, 150))
        f = font("ExtraBold", 78)
        d.text((140, 330), "Estimez votre bien", font=f, fill=WHITE)
        d.text((140, 425), "gratuitement, en 2 min.", font=f, fill=WHITE)
        d.text((140, 560), "Puis vendez sans agence, sans commission.", font=font("SemiBold", 36), fill=PALE)
        d.rounded_rectangle((140, 660, 820, 770), radius=55, fill=WHITE)
        text_center(d, 480, 688, "achetemamaison.fr", font("Bold", 50), BRAND)
        badge(im, 140, 830, 380, 118, "ios")
        badge(im, 550, 830, 380, 118, "android")
        m = mascot.resize((760, 760))
        paste_alpha(im, m, (w - 760 - 90, h - 760 - 20))
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (w, h) in {"vertical": (1080, 1920), "carre": (1080, 1080), "paysage": (1920, 1080)}.items():
        path = f"{OUT}/fin-video-{name}.png"
        render(w, h, name).save(path, optimize=True)
        print("->", path, os.path.getsize(path) // 1024, "Ko")


if __name__ == "__main__":
    main()
