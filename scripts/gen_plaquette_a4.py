"""Plaquette A4 recto (210×297 mm, 300 dpi) — présentation Achète ma maison, jointe au courrier leboncoin.
Sorties : backend/media/plaquette-a4.pdf et .png. Usage : python scripts/gen_plaquette_a4.py
"""
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, M = 2480, 3508, 170
FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT = "/app/backend/media"
BRAND, DEEP, INK, MUTED, BORDER, WHITE = (22, 86, 201), (11, 59, 143), (15, 27, 45), (91, 107, 130), (226, 232, 240), (255, 255, 255)
SOFT, GREEN = (240, 245, 255), (22, 163, 74)
URL = "https://achetemamaison.fr/?utm_source=courrier&utm_medium=plaquette&utm_campaign=leboncoin"


def font(name, size):
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(d, x, y, text, f, fill, max_w, lh=1.38):
    for line in wrap(d, text, f, max_w):
        d.text((x, y), line, font=f, fill=fill)
        y += int(f.size * lh)
    return y


def rounded_photo(path, size, radius=36):
    im = ImageOps.fit(Image.open(path).convert("RGB"), size, Image.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    im.putalpha(mask)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    tw = W - 2 * M

    # ---- Bandeau haut
    d.rectangle((0, 0, W, 980), fill=DEEP)
    d.rectangle((0, 980, W, 1000), fill=BRAND)
    logo = Image.open(f"{ASSETS}/images/logo-wordmark-dark.png").convert("RGBA")
    logo = logo.resize((640, round(640 * logo.height / logo.width)))
    im.paste(logo, (M, 130), logo)
    d.text((M, 320), "L'application qui accompagne", font=font("ExtraBold", 92), fill=WHITE)
    d.text((M, 430), "le vendeur particulier", font=font("ExtraBold", 92), fill=WHITE)
    d.text((M, 540), "de l'estimation à la vente", font=font("ExtraBold", 92), fill=(190, 212, 255))
    y = para(d, M, 690, "Estimation gratuite en 2 minutes, sans inscription ni rappel commercial. Puis photos, annonce et dossier de vente prêts à publier.", font("Medium", 40), (220, 230, 250), 1500)
    for i, t in enumerate(("App Store", "Google Play", "achetemamaison.fr")):
        f = font("Bold", 32)
        tw_ = d.textlength(t, font=f) + 60
        x = M + sum(d.textlength(p, font=f) + 60 + 24 for p in ("App Store", "Google Play", "achetemamaison.fr")[:i])
        d.rounded_rectangle((x, 850, x + tw_, 850 + 72), 36, fill=WHITE)
        d.text((x + 30, 866), t, font=f, fill=DEEP)
    # Noisette
    m = Image.open(f"{ASSETS}/mascot/noisette-telephone.webp").convert("RGBA").resize((760, 760))
    im.paste(m, (W - M - 700, 200), m)

    # ---- 3 étapes
    y = 1090
    d.text((M, y), "Un parcours en 3 étapes", font=font("ExtraBold", 60), fill=INK)
    y += 100
    gap, cw = 40, (tw - 2 * 40) // 3
    steps = [
        ("web/step1-phone.jpg", "1. Estimation", "Plusieurs modèles de valorisation croisés avec toutes les ventes réelles (base DVF), les caractéristiques du bien et son environnement. Fourchette de prix argumentée, en moins de 2 minutes."),
        ("web/step2-annonce.jpg", "2. Mise en vente", "Analyse de l'environnement, photos retouchées par IA sans altérer le bien, texte d'annonce rédigé automatiquement et export « annonce complète » prêt à publier."),
        ("web/step3-notaire.jpg", "3. Vendu", "Liste dynamique des diagnostics et documents obligatoires, lecture automatique des pièces (OCR) et dossier de vente complet pour le notaire."),
    ]
    for i, (img, title, txt) in enumerate(steps):
        x = M + i * (cw + gap)
        ph = rounded_photo(f"{ASSETS}/{img}", (cw, 440))
        im.paste(ph, (x, y), ph)
        d.rounded_rectangle((x + 24, y + 24, x + 90, y + 90), 33, fill=BRAND)
        d.text((x + 57, y + 57), str(i + 1), font=font("ExtraBold", 40), fill=WHITE, anchor="mm")
        d.text((x, y + 480), title, font=font("Bold", 44), fill=INK)
        para(d, x, y + 545, txt, font("Regular", 31), MUTED, cw)
    y += 900

    # ---- Avant / après photos IA
    d.rounded_rectangle((M, y, W - M, y + 720), 48, fill=SOFT)
    d.text((M + 60, y + 50), "Retouche photo par IA — le bien n'est jamais modifié", font=font("Bold", 46), fill=INK)
    left_w = 1040
    para(d, M + 60, y + 125, "Lumière, cadrage, ciel et netteté sont corrigés ; murs, volumes et équipements restent strictement identiques. Des annonces plus attractives, sans tromper l'acheteur.", font("Regular", 32), MUTED, left_w)
    pw, phh = 440, 293
    bx = W - M - 60 - 2 * pw - 30
    for j, (f_, lab) in enumerate((("demo-before.jpg", "Avant"), ("demo-after.jpg", "Après"))):
        ph = rounded_photo(f"{ASSETS}/images/{f_}", (pw, phh), 28)
        px = bx + j * (pw + 30)
        im.paste(ph, (px, y + 130), ph)
        d.rounded_rectangle((px + 20, y + 150, px + 170, y + 206), 28, fill=WHITE if j == 0 else GREEN)
        d.text((px + 95, y + 178), lab, font=font("Bold", 30), fill=INK if j == 0 else WHITE, anchor="mm")
    # chiffres clés sous le texte
    kp = [("< 2 min", "pour une estimation"), ("0 €", "sans inscription"), ("100 %", "des ventes DVF")]
    for k, (big, small) in enumerate(kp):
        kx = M + 60 + k * 330
        d.text((kx, y + 330), big, font=font("ExtraBold", 64), fill=BRAND)
        d.text((kx, y + 410), small, font=font("Regular", 28), fill=MUTED)
    # arguments
    args = ["Des annonces au juste prix dès la publication", "Photos et textes complets : plus de contacts", "Moins d'annonces dormantes ou surévaluées"]
    for k, a in enumerate(args):
        ay = y + 500 + k * 62
        cx, cy = M + 80, ay + 28
        d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=GREEN)
        d.line((cx - 9, cy, cx - 3, cy + 7, cx + 10, cy - 8), fill=WHITE, width=5, joint="curve")
        d.text((M + 125, ay), a, font=font("Medium", 34), fill=INK)
    y += 790

    # ---- Bas : QR + contact
    d.line((M, y, W - M, y), fill=BORDER, width=3)
    y += 50
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data(URL)
    qr.make(fit=True)
    q = qr.make_image(fill_color=DEEP, back_color="white").convert("RGB").resize((360, 360), Image.NEAREST)
    im.paste(q, (W - M - 360, y))
    d.text((W - M - 180, y + 385), "Testez l'application", font=font("Medium", 28), fill=MUTED, anchor="mm")
    d.text((M, y), "Parlons-en", font=font("ExtraBold", 56), fill=INK)
    para(d, M, y + 85, "Démonstration de 20 minutes, en visio ou dans vos locaux, avec une estimation en direct sur le bien de votre choix.", font("Regular", 34), INK, 1250)
    d.text((M, y + 215), "Anthony Goemaere — Co-fondateur", font=font("Bold", 36), fill=INK)
    d.text((M, y + 268), "contact@achetemamaison.fr  ·  achetemamaison.fr", font=font("Medium", 34), fill=BRAND)
    m2 = Image.open(f"{ASSETS}/mascot/noisette-pouce.webp").convert("RGBA").resize((300, 300))
    im.paste(m2, (W - M - 720, y + 30), m2)

    foot = "Nymbrum Corporation — SAS au capital de 1 000 € — RCS Blois 132 452 947 — 731 route de Touchebrault, 41230 Soings-en-Sologne"
    f = font("Regular", 24)
    d.text(((W - d.textlength(foot, font=f)) / 2, H - 110), foot, font=f, fill=MUTED)
    print("bas du contenu y =", y + 450, "/", H)

    im.save(f"{OUT}/plaquette-a4.png", dpi=(300, 300), optimize=True)
    im.save(f"{OUT}/plaquette-a4.pdf", "PDF", resolution=300.0)
    print("->", f"{OUT}/plaquette-a4.pdf")


if __name__ == "__main__":
    main()
