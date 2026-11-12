"""Lettre postale A5 recto (148×210 mm, 300 dpi = 1748×2480 px) : Noisette + QR code vers l'estimation gratuite.
Sorties : backend/media/lettre-vendeur-a5.png et .pdf (prêt à imprimer).
Usage : python scripts/gen_lettre_a5.py
"""
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

W, H = 1748, 2480  # A5 à 300 dpi
M = 130  # marge
FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT = "/app/backend/media"
URL = "https://achetemamaison.fr/estimation-maison?utm_source=courrier&utm_medium=lettre&utm_campaign=pige"
BRAND, DEEP, INK, MUTED, LIGHT, BORDER, WHITE, GREEN = (22, 86, 201), (11, 59, 143), (15, 27, 45), (91, 107, 130), (244, 247, 252), (226, 232, 240), (255, 255, 255), (30, 158, 106)


def font(name, size):
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(d, x, y, text, f, fill, max_w, lh=1.4):
    for line in wrap(d, text, f, max_w):
        d.text((x, y), line, font=f, fill=fill)
        y += int(f.size * lh)
    return y


def main():
    os.makedirs(OUT, exist_ok=True)
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)

    # Bandeau haut
    d.rectangle((0, 0, W, 300), fill=DEEP)
    logo = Image.open(f"{ASSETS}/images/logo-wordmark-dark.png").convert("RGBA")
    logo = logo.resize((560, round(560 * logo.height / logo.width)))
    im.paste(logo, (M, 150 - logo.height // 2), logo)
    d.text((W - M - d.textlength("Estimation gratuite · sans agence", font=font("SemiBold", 34)), 128), "Estimation gratuite · sans agence", font=font("SemiBold", 34), fill=(207, 224, 255))

    y = 380
    d.text((M, y), "Vous vendez votre bien par vous-même ?", font=font("ExtraBold", 66), fill=INK)
    y += 90
    d.text((M, y), "Bravo. Vérifions ensemble que vous êtes au bon prix.", font=font("SemiBold", 40), fill=BRAND)
    y += 110

    body = font("Regular", 36)
    col_w = W - 2 * M - 520  # colonne texte à gauche de Noisette
    y = para(d, M, y, "Madame, Monsieur,", body, INK, col_w)
    y += 20
    y = para(d, M, y, "Nous avons remarqué que vous vendez votre logement sans agence. C'est le bon choix : vous gardez le contrôle, et plusieurs milliers d'euros de commission.", body, INK, col_w)
    y += 20
    y = para(d, M, y, "Le seul risque, c'est le prix. Trop haut, le bien reste des mois en ligne ; trop bas, vous perdez de l'argent. Nous sommes des professionnels de l'immobilier et nous avons créé un outil qui estime votre bien en 2 minutes à partir des ventes réelles enregistrées autour de chez vous.", body, INK, col_w)
    y += 20
    y = para(d, M, y, "C'est gratuit, sans inscription, et personne ne vous rappellera : vous obtenez simplement un prix fiable, avec la fourchette et les ventes qui le justifient.", body, INK, col_w)

    # Noisette à droite
    m = Image.open(f"{ASSETS}/mascot/noisette-telephone.webp").convert("RGBA").resize((520, 520))
    im.paste(m, (W - M - 500, 700), m)

    # Encart QR
    y = max(y + 60, 1420)
    d.rounded_rectangle((M, y, W - M, y + 560), radius=40, fill=LIGHT, outline=BORDER, width=3)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data(URL)
    qr.make(fit=True)
    qimg = qr.make_image(fill_color=INK, back_color=WHITE).convert("RGB").resize((440, 440))
    im.paste(qimg, (M + 60, y + 60))
    tx = M + 60 + 440 + 70
    d.text((tx, y + 70), "Estimez votre bien en 2 minutes", font=font("ExtraBold", 46), fill=INK)
    d.text((tx, y + 140), "1. Scannez le QR code avec votre téléphone", font=font("Medium", 34), fill=INK)
    d.text((tx, y + 195), "2. Indiquez l'adresse et quelques détails", font=font("Medium", 34), fill=INK)
    d.text((tx, y + 250), "3. Obtenez votre prix, avec sa fourchette", font=font("Medium", 34), fill=INK)
    d.text((tx, y + 330), "ou rendez-vous sur", font=font("Regular", 30), fill=MUTED)
    d.rounded_rectangle((tx, y + 380, tx + 640, y + 470), radius=45, fill=BRAND)
    s = "achetemamaison.fr"
    d.text((tx + (640 - d.textlength(s, font=font("Bold", 42))) / 2, y + 400), s, font=font("Bold", 42), fill=WHITE)

    # Promesses
    y += 620
    x = M
    for t in ("Gratuit", "Sans inscription", "Aucun rappel commercial", "Ventes réelles (DVF)"):
        d.ellipse((x, y + 4, x + 36, y + 40), fill=GREEN)
        d.line((x + 9, y + 22, x + 16, y + 30, x + 28, y + 13), fill=WHITE, width=5)
        d.text((x + 50, y), t, font=font("SemiBold", 28), fill=INK)
        x += 50 + int(d.textlength(t, font=font("SemiBold", 28))) + 70

    # Signature + mentions
    y += 110
    y = para(d, M, y, "Nous vous souhaitons une belle vente,", body, INK, W - 2 * M)
    d.text((M, y + 10), "Sébastien Ghelfi & Anthony Goemaere", font=font("Bold", 34), fill=INK)
    d.text((M, y + 58), "Co-fondateurs d'Achète ma maison · Professionnels de l'immobilier", font=font("Regular", 28), fill=MUTED)

    foot = font("Regular", 22)
    d.line((M, H - 170, W - M, H - 170), fill=BORDER, width=2)
    para(d, M, H - 150, "Nymbrum Corporation, SAS au capital de 1 000 € · RCS Blois 132 452 947 · 731 route de Touchebrault, 41230 Soings-en-Sologne · contact@achetemamaison.fr. "
         "Courrier adressé à l'occupant à partir d'une annonce publique de vente. Vous pouvez vous opposer à tout nouvel envoi en écrivant à contact@achetemamaison.fr.", foot, MUTED, W - 2 * M, lh=1.35)

    png = f"{OUT}/lettre-vendeur-a5.png"
    pdf = f"{OUT}/lettre-vendeur-a5.pdf"
    im.save(png, dpi=(300, 300), optimize=True)
    im.save(pdf, "PDF", resolution=300.0)
    print("->", png, os.path.getsize(png) // 1024, "Ko |", pdf, os.path.getsize(pdf) // 1024, "Ko")


if __name__ == "__main__":
    main()
