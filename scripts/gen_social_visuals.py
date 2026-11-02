"""Visuels réseaux sociaux : post de présentation (1080×1350) et bannière Facebook (1640×624).
Sortie : frontend/assets/images/social-post.jpg, social-cover.jpg. Pur Pillow (aucune génération IA).
Usage : python scripts/gen_social_visuals.py
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = "/app/frontend/assets/images"
FONTS = "/app/frontend/assets/fonts"
BRAND, DEEP, SOFT, INK, MUTED, WHITE, GREEN, LIGHT = "#1656C9", "#0B3B8F", "#7FA3E3", "#0F1B2D", "#5B6B82", "#FFFFFF", "#1E9E6A", "#E8F0FD"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def gradient(w: int, h: int, c1=(11, 59, 143), c2=(22, 86, 201)) -> Image.Image:
    base = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(base)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line((0, y, w, y), fill=tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    # halo doux en haut à droite
    halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((w * 0.45, -h * 0.35, w * 1.25, h * 0.45), fill=(127, 163, 227, 90))
    halo = halo.filter(ImageFilter.GaussianBlur(120))
    return Image.alpha_composite(base.convert("RGBA"), halo).convert("RGB")


def pill(d: ImageDraw.ImageDraw, xy, text, f, bg, fg, pad=(18, 10)):
    x, y = xy
    tw = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + tw + 2 * pad[0], y + f.size + 2 * pad[1]), (f.size + 2 * pad[1]) // 2, fill=bg)
    d.text((x + pad[0], y + pad[1] - 2), text, font=f, fill=fg)
    return x + tw + 2 * pad[0]


def check(d, x, y, r=11, color=GREEN):
    d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=color)
    d.line((x + r * 0.55, y + r, x + r * 0.9, y + r * 1.4, x + r * 1.5, y + r * 0.6), fill=WHITE, width=3)


def store_badge(d, x, y, big, small, scale=1.0):
    w, h = round(190 * scale), round(56 * scale)
    d.rounded_rectangle((x, y, x + w, y + h), round(12 * scale), fill="#111111", outline="#3A3A3A", width=1)
    d.text((x + 16 * scale, y + 10 * scale), small, font=font("Medium", round(11 * scale)), fill="#D6D6D6")
    d.text((x + 16 * scale, y + 24 * scale), big, font=font("SemiBold", round(19 * scale)), fill=WHITE)
    return x + w


def phone(width: int) -> Image.Image:
    """Mockup de téléphone avec un écran d'estimation dessiné (pas de capture réelle)."""
    w = width
    h = round(w * 2.05)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = round(w * 0.14)
    d.rounded_rectangle((0, 0, w, h), r, fill="#0F1B2D")
    m = round(w * 0.035)
    d.rounded_rectangle((m, m, w - m, h - m), r - m, fill="#F3F6FB")
    # encoche
    d.rounded_rectangle((w * 0.35, m + 8, w * 0.65, m + 8 + w * 0.06), w * 0.03, fill="#0F1B2D")
    s = w / 390  # échelle « points »
    # en-tête app
    d.text((28 * s, 70 * s), "Votre estimation", font=font("ExtraBold", round(24 * s)), fill=INK)
    d.text((28 * s, 104 * s), "12 rue des Lilas · Blois (41)", font=font("Medium", round(13 * s)), fill=MUTED)
    # photo
    photo = Image.open(f"{OUT}/demo-after.jpg").convert("RGB")
    pw, ph = round(334 * s), round(150 * s)
    sc = max(pw / photo.width, ph / photo.height)
    photo = photo.resize((round(photo.width * sc), round(photo.height * sc)))
    photo = photo.crop(((photo.width - pw) // 2, (photo.height - ph) // 2, (photo.width - pw) // 2 + pw, (photo.height - ph) // 2 + ph))
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, ph), round(16 * s), fill=255)
    im.paste(photo, (round(28 * s), round(132 * s)), mask)
    # carte prix
    cy = 300 * s
    d.rounded_rectangle((28 * s, cy, 362 * s, cy + 150 * s), 18 * s, fill=WHITE, outline="#DCE5F2")
    d.text((46 * s, cy + 16 * s), "PRIX DE VENTE CONSEILLÉ", font=font("Bold", round(10 * s)), fill=MUTED)
    d.text((46 * s, cy + 34 * s), "248 000 €", font=font("ExtraBold", round(36 * s)), fill=BRAND)
    d.text((46 * s, cy + 82 * s), "Fourchette 235 000 – 262 000 €", font=font("Medium", round(12 * s)), fill=MUTED)
    d.rounded_rectangle((46 * s, cy + 106 * s, 344 * s, cy + 114 * s), 4 * s, fill=LIGHT)
    d.rounded_rectangle((110 * s, cy + 106 * s, 290 * s, cy + 114 * s), 4 * s, fill=SOFT)
    d.rounded_rectangle((196 * s, cy + 100 * s, 206 * s, cy + 120 * s), 3 * s, fill=BRAND)
    pill(d, (46 * s, cy + 124 * s - 8 * s), "Confiance élevée", font("Bold", round(10 * s)), "#E3F6EC", GREEN, (10 * s, 5 * s))
    # lignes fonctionnalités
    y = cy + 172 * s
    for t in ("Annonce rédigée par IA", "Photos retouchées, fidèles au bien", "Analyse du quartier", "Documents pour le notaire"):
        check(d, 32 * s, y + 2 * s, round(10 * s))
        d.text((62 * s, y), t, font=font("SemiBold", round(14 * s)), fill=INK)
        y += 34 * s
    # bouton
    d.rounded_rectangle((28 * s, y + 10 * s, 362 * s, y + 60 * s), 14 * s, fill=BRAND)
    bt = "Préparer la mise en vente"
    d.text(((w - d.textlength(bt, font=font("Bold", round(15 * s)))) / 2, y + 24 * s), bt, font=font("Bold", round(15 * s)), fill=WHITE)
    return im


def shadow_paste(base: Image.Image, im: Image.Image, xy, blur=40, offset=(0, 30), alpha=120):
    sh = Image.new("RGBA", (im.width + blur * 4, im.height + blur * 4), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: min(v, alpha))
    sh.paste((0, 0, 0, alpha), (blur * 2, blur * 2), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.paste(sh, (xy[0] - blur * 2 + offset[0], xy[1] - blur * 2 + offset[1]), sh)
    base.paste(im, xy, im)


def post():
    W, H = 1080, 1350
    im = gradient(W, H)
    d = ImageDraw.Draw(im)
    logo = Image.open(f"{OUT}/logo-wordmark-dark.png").convert("RGBA")
    logo = logo.resize((360, round(360 * logo.height / logo.width)))
    im.paste(logo, (64, 64), logo)
    pill(d, (64, 190), "NOUVEAU · DISPONIBLE SUR IPHONE ET ANDROID", font("Bold", 18), "#FFFFFF", BRAND, (18, 10))
    y = 262
    for ln in ("Vendez votre", "maison sans", "agence."):
        d.text((64, y), ln, font=font("ExtraBold", 78), fill=WHITE)
        y += 86
    y += 26
    for t in ("Estimation gratuite en 2 min", "Annonce & photos IA", "Dossier prêt pour le notaire"):
        check(d, 64, y + 6, 13, "#7FE0B0")
        d.text((102, y), t, font=font("SemiBold", 25), fill="#EAF1FF")
        y += 46
    # téléphone
    ph = phone(450)
    shadow_paste(im, ph, (590, 560), blur=50, offset=(0, 40), alpha=140)
    # bas : prix + badges + url
    d.rounded_rectangle((64, H - 250, 520, H - 180), 18, fill="#0B3B8F")
    d.text((84, H - 232), "49 € une fois · 0 % de commission", font=font("Bold", 22), fill="#CFE0FF")
    x = store_badge(d, 64, H - 150, "l’App Store", "Télécharger dans", 1.0)
    store_badge(d, x + 14, H - 150, "Google Play", "Disponible sur", 1.0)
    d.text((64, H - 70), "achetemamaison.fr", font=font("ExtraBold", 26), fill=WHITE)
    im.save(f"{OUT}/social-post.jpg", quality=92, optimize=True)
    print("->", f"{OUT}/social-post.jpg")


def cover():
    W, H = 1640, 624
    im = gradient(W, H)
    d = ImageDraw.Draw(im)
    # zone sûre mobile ≈ 1250 px centrés : textes entre x=200 et x=1440
    logo = Image.open(f"{OUT}/logo-wordmark-dark.png").convert("RGBA")
    logo = logo.resize((380, round(380 * logo.height / logo.width)))
    im.paste(logo, (210, 120), logo)
    d.text((210, 250), "Vendez votre bien sans agence,", font=font("ExtraBold", 50), fill=WHITE)
    d.text((210, 310), "avec les outils d’un pro.", font=font("ExtraBold", 50), fill="#CFE0FF")
    x = 210
    for t in ("Estimation gratuite", "Annonce & photos IA", "Dossier notaire"):
        x0 = x
        x = pill(d, (x, 392), "     " + t, font("Bold", 20), "#FFFFFF", BRAND, (18, 10)) + 12
        check(d, x0 + 16, 401, 10)
    d.text((210, 470), "49 € une fois · 0 % de commission · achetemamaison.fr", font=font("SemiBold", 22), fill="#EAF1FF")
    ph = phone(300)
    ph = ph.rotate(-8, resample=Image.BICUBIC, expand=True)
    shadow_paste(im, ph, (1120, 60), blur=40, offset=(0, 30), alpha=130)
    im.save(f"{OUT}/social-cover.jpg", quality=92, optimize=True)
    print("->", f"{OUT}/social-cover.jpg")


if __name__ == "__main__":
    post()
    cover()
