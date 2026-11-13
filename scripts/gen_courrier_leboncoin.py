"""Courrier A4 (210×297 mm, 300 dpi) avec en-tête Achète ma maison — proposition de partenariat leboncoin.
Sorties : backend/media/courrier-leboncoin.pdf et .png. Usage : python scripts/gen_courrier_leboncoin.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

W, H, M = 2480, 3508, 236  # A4 à 300 dpi, marge 20 mm
FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT = "/app/backend/media"
BRAND, DEEP, INK, MUTED, BORDER, WHITE = (22, 86, 201), (11, 59, 143), (15, 27, 45), (91, 107, 130), (226, 232, 240), (255, 255, 255)
DATE = "Soings-en-Sologne, le 13 novembre 2026"


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


def para(d, x, y, text, f, fill, max_w, lh=1.42):
    for line in wrap(d, text, f, max_w):
        d.text((x, y), line, font=f, fill=fill)
        y += int(f.size * lh)
    return y


def rich(d, x, y, bold, rest, fb, fr, fill, max_w, lh=1.42):
    """Paragraphe commençant par un segment en gras."""
    bw = d.textlength(bold + " ", font=fb)
    d.text((x, y), bold, font=fb, fill=fill)
    # première ligne après le gras : re-découpe avec la largeur restante
    first = wrap(d, rest, fr, max_w - bw)
    d.text((x + bw, y), first[0], font=fr, fill=fill)
    y += int(fr.size * lh)
    remaining = rest[len(first[0]):].strip()
    for line in wrap(d, remaining, fr, max_w):
        d.text((x, y), line, font=fr, fill=fill)
        y += int(fr.size * lh)
    return y


def main():
    os.makedirs(OUT, exist_ok=True)
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    body, bold = font("Regular", 40), font("Bold", 40)
    tw = W - 2 * M

    # En-tête
    logo = Image.open(f"{ASSETS}/images/logo-wordmark.png").convert("RGBA")
    logo = logo.resize((620, round(620 * logo.height / logo.width)))
    im.paste(logo, (M, 150), logo)
    hx = W - M
    for i, t in enumerate(("Nymbrum Corporation", "731 route de Touchebrault", "41230 Soings-en-Sologne", "contact@achetemamaison.fr", "achetemamaison.fr")):
        f = font("Bold" if i == 0 else "Regular", 30)
        d.text((hx - d.textlength(t, font=f), 150 + i * 42), t, font=f, fill=INK if i == 0 else MUTED)
    d.line((M, 390, W - M, 390), fill=BRAND, width=5)

    # Destinataire + date
    y = 470
    for i, t in enumerate(("SCM LOCAL — leboncoin", "À l'attention de la Direction Immobilier", "et de la Direction des Partenariats", "24 rue des Jeûneurs", "75002 Paris")):
        d.text((W - M - 900, y + i * 50), t, font=font("Bold" if i == 0 else "Regular", 36), fill=INK)
    d.text((M, 470), DATE, font=font("Regular", 36), fill=INK)
    y = 760
    d.text((M, y), "Objet : Proposition de partenariat — estimation immobilière intégrée au dépôt d'annonce", font=font("Bold", 38), fill=INK)
    y += 56
    d.text((M, y), "Réf. : votre ticket n° 129820", font=font("Regular", 34), fill=MUTED)
    y += 90

    y = para(d, M, y, "Madame, Monsieur,", body, INK, tw) + 18
    y = para(d, M, y, "À la suite de l'échange avec votre service client (ticket n° 129820), qui m'a invité à vous adresser ma demande par courrier, je me permets de vous présenter Achète ma maison et la proposition de partenariat que nous souhaiterions étudier avec leboncoin Immobilier.", body, INK, tw) + 18
    y = rich(d, M, y, "Qui nous sommes.", "Nymbrum Corporation édite Achète ma maison, une application disponible sur l'App Store, Google Play et sur achetemamaison.fr. Nous sommes des professionnels de l'immobilier. Après des années d'estimation et de vente sur le terrain, nous avons conçu un moteur d'estimation qui croise plusieurs modèles de valorisation, l'intégralité des ventes réelles enregistrées (base DVF), les caractéristiques précises du bien et l'analyse de son environnement, pour délivrer en moins de deux minutes une fourchette de prix fiable et argumentée. L'estimation est gratuite, sans inscription et sans rappel commercial. Au-delà, l'application accompagne le particulier jusqu'à la mise en vente : analyse de l'environnement, photos retouchées par intelligence artificielle sans altération du bien, texte d'annonce rédigé automatiquement, liste des diagnostics et documents obligatoires.", bold, body, INK, tw) + 18
    y = rich(d, M, y, "Pourquoi leboncoin.", "Nos utilisateurs sont des vendeurs particuliers qui s'apprêtent à publier une annonce, avec un prix cohérent avec le marché, des photos de qualité et un texte complet. Une grande partie d'entre eux publie déjà sur leboncoin : nous les y encourageons dans l'application via un export « annonce complète ».", bold, body, INK, tw) + 18
    d.text((M, y), "Ce que nous proposons d'étudier ensemble :", font=bold, fill=INK)
    y += 60
    items = [
        ("Estimation intégrée au dépôt d'annonce :", "proposer notre estimation instantanée aux particuliers au moment où ils déposent une annonce, pour fixer un prix juste dès la publication."),
        ("Publication en un clic :", "dépôt de l'annonce (texte, photos, caractéristiques) sur leboncoin depuis notre application, via votre API partenaires."),
        ("Visibilité croisée et offre commune :", "leboncoin recommandé comme plateforme de diffusion dans notre application ; conditions préférentielles sur vos options de visibilité pour les vendeurs ayant préparé leur annonce avec Achète ma maison."),
    ]
    for i, (b, r) in enumerate(items):
        d.text((M + 20, y), f"{i + 1}.", font=bold, fill=BRAND)
        y = rich(d, M + 90, y, b, r, bold, body, INK, tw - 90) + 8
    y += 10
    y = para(d, M, y, "L'intérêt pour leboncoin est direct : des annonces mieux positionnées en prix, plus complètes et mieux présentées, donc davantage de contacts, des ventes plus rapides et moins d'annonces dormantes ou surévaluées.", body, INK, tw) + 18
    y = para(d, M, y, "Nous serions heureux de vous présenter l'application lors d'un échange de vingt minutes, en visioconférence ou dans vos locaux, avec une estimation en direct sur le bien de votre choix et nos premiers chiffres d'usage. Vous pouvez nous joindre à contact@achetemamaison.fr.", body, INK, tw) + 18
    y = para(d, M, y, "Je vous remercie de l'attention que vous porterez à cette proposition et vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.", body, INK, tw) + 70

    d.text((W - M - 900, y), "Anthony Goemaere", font=font("Bold", 38), fill=INK)
    d.text((W - M - 900, y + 50), "Co-fondateur — Achète ma maison", font=font("Regular", 34), fill=MUTED)
    d.text((W - M - 900, y + 96), "Nymbrum Corporation", font=font("Regular", 34), fill=MUTED)
    y += 260
    d.text((M, y), "Pièces jointes : plaquette de présentation (1 page) ; extrait des avis utilisateurs.", font=font("Regular", 30), fill=MUTED)

    # Pied de page
    d.line((M, H - 230, W - M, H - 230), fill=BORDER, width=2)
    foot = "Nymbrum Corporation — SAS au capital de 1 000 € — RCS Blois 132 452 947 — SIRET 132 452 947 00014 — TVA FR02132452947 — 731 route de Touchebrault, 41230 Soings-en-Sologne"
    f = font("Regular", 24)
    d.text(((W - d.textlength(foot, font=f)) / 2, H - 200), foot, font=f, fill=MUTED)
    print("dernière ligne du corps à y =", y, "/", H)

    im.save(f"{OUT}/courrier-leboncoin.png", dpi=(300, 300), optimize=True)
    im.save(f"{OUT}/courrier-leboncoin.pdf", "PDF", resolution=300.0)
    print("->", f"{OUT}/courrier-leboncoin.pdf")


if __name__ == "__main__":
    main()
