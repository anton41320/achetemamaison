"""Vidéo verticale (1080×1920, 30 i/s, ~24 s) : rapidité de l'estimation + arguments de calcul.
Rendu image par image avec Pillow, encodage H.264 via imageio-ffmpeg.
Usage : python scripts/gen_estimation_video.py  ->  /app/backend/media/estimation-rapide.mp4 
"""
import math
import os
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT_DIR = "/app/backend/media"
OUT = f"{OUT_DIR}/estimation-rapide.mp4"

BRAND, DEEP, INK, MUTED, WHITE, GREEN, LIGHT, BORDER, ORANGE = (
    (22, 86, 201), (11, 59, 143), (15, 27, 45), (91, 107, 130), (255, 255, 255), (30, 158, 106), (244, 247, 252), (226, 232, 240), (234, 120, 40),
)


def font(name, size):
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def ease(t):  # smoothstep
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def seg(t, a, b):
    """progression 0→1 de t entre a et b (secondes)."""
    return ease((t - a) / (b - a)) if b > a else 1.0


def rounded(d, box, r, fill, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def text_center(d, y, s, f, fill, x0=0, x1=W):
    w = d.textlength(s, font=f)
    d.text(((x0 + x1 - w) / 2, y), s, font=f, fill=fill)


def gradient_bg():
    im = Image.new("RGB", (W, H), DEEP)
    px = im.load()
    for y in range(H):
        k = y / H
        c = tuple(int(DEEP[i] + (BRAND[i] - DEEP[i]) * k) for i in range(3))
        for x in range(W):
            px[x, y] = c
    return im


BG = gradient_bg()
LOGO = Image.open(f"{ASSETS}/images/logo-wordmark-dark.png").convert("RGBA")
LOGO = LOGO.resize((520, round(520 * LOGO.height / LOGO.width)))
MASCOT = {k: Image.open(f"{ASSETS}/mascot/noisette-{k}.webp").convert("RGBA") for k in ("telephone", "pouce")}


def mascot(im, pose, size, xy, alpha=1.0):
    m = MASCOT[pose].resize((size, size))
    if alpha < 1:
        a = m.getchannel("A").point(lambda v: int(v * alpha))
        m.putalpha(a)
    im.paste(m, xy, m)


def stopwatch(d, t_start, t, x, y, running=True, final=None):
    """Chrono mm:ss affiché en haut."""
    secs = final if final is not None else max(0, t - t_start) * 60 / 1.0  # 1 s réelle = 60 s simulées… non : on affiche un chrono réaliste accéléré
    secs = min(secs, 119)
    label = f"{int(secs // 60)}:{int(secs % 60):02d}"
    rounded(d, (x, y, x + 300, y + 76), 38, (52, 112, 220) if running else GREEN)
    d.ellipse((x + 22, y + 22, x + 54, y + 54), outline=WHITE, width=4)
    d.line((x + 38, y + 38, x + 38, y + 28), fill=WHITE, width=4)
    d.text((x + 74, y + 14), label, font=font("Bold", 38), fill=WHITE)
    d.text((x + 196, y + 26), "chrono", font=font("Medium", 22), fill=WHITE)


def card(im, box, r=36):
    d = ImageDraw.Draw(im)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + 18, box[2], box[3] + 18), radius=r, fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    im.paste(shadow, (0, 0), shadow)
    d.rounded_rectangle(box, radius=r, fill=WHITE)


# ---------- Scènes ----------
ADDRESS = "12 rue des Lilas, 41000 Blois"
FIELDS = [("Surface habitable", "128 m²"), ("Terrain", "650 m²"), ("Pièces", "5"), ("Année", "1998"), ("État général", "Bon")]
STEPS = [
    ("Ventes réelles autour du bien", "Base DVF · 36 ventes sur 24 mois · rayon 1,5 km"),
    ("Sélection des comparables", "12 maisons similaires · surface, terrain, époque"),
    ("Modèle hédonique", "Poids de chaque critère : surface, état, année, terrain"),
    ("Ajustement marché local", "Tendance 12 mois du secteur : +3,2 %"),
    ("Croisement des modèles", "Fourchette basse / haute + indice de fiabilité"),
]


def scene_intro(im, t):
    d = ImageDraw.Draw(im)
    k = seg(t, 0, 0.8)
    lo = LOGO.copy()
    lo.putalpha(lo.getchannel("A").point(lambda v: int(v * k)))
    im.paste(lo, ((W - lo.width) // 2, 260), lo)
    k2 = seg(t, 0.5, 1.4)
    f = font("ExtraBold", 84)
    for i, line in enumerate(("Combien vaut", "votre maison ?")):
        c = tuple(int(DEEP[j] + (255 - DEEP[j]) * k2) for j in range(3))
        text_center(d, 560 + i * 100 - int((1 - k2) * 40), line, f, c)
    k3 = seg(t, 1.2, 2.0)
    if k3 > 0:
        c = tuple(int(DEEP[j] + (207 - DEEP[j]) * k3) for j in range(3))
        text_center(d, 800, "Réponse précise en moins de 2 minutes.", font("SemiBold", 40), c)
        text_center(d, 860, "Gratuit · sans inscription", font("Medium", 34), c)
    mascot(im, "telephone", 620, ((W - 620) // 2, 980), alpha=seg(t, 1.0, 1.9))


def scene_form(im, t, t0):
    d = ImageDraw.Draw(im)
    text_center(d, 120, "1. Vous décrivez votre bien", font("ExtraBold", 54), WHITE)
    stopwatch(d, t0, t, (W - 300) // 2, 200, final=(t - t0) * 9)
    card(im, (80, 320, W - 80, 1560))
    d = ImageDraw.Draw(im)
    d.text((130, 370), "Adresse du bien", font=font("SemiBold", 30), fill=MUTED)
    rounded(d, (130, 420, W - 130, 520), 24, LIGHT, BORDER)
    n = int(len(ADDRESS) * seg(t, t0 + 0.2, t0 + 2.2))
    d.text((160, 450), ADDRESS[:n] + ("|" if (t * 2) % 1 < 0.5 and n < len(ADDRESS) else ""), font=font("Medium", 36), fill=INK)
    if n == len(ADDRESS):
        d.ellipse((W - 190, 450, W - 150, 490), fill=GREEN)
        d.line((W - 182, 470, W - 172, 480, W - 158, 460), fill=WHITE, width=5)
    for i, (lab, val) in enumerate(FIELDS):
        k = seg(t, t0 + 2.4 + i * 0.45, t0 + 2.9 + i * 0.45)
        if k <= 0:
            continue
        y = 580 + i * 150
        rounded(d, (130, y, W - 130, y + 120), 24, LIGHT, BORDER)
        d.text((160, y + 20), lab, font=font("SemiBold", 28), fill=MUTED)
        vv = val[: int(len(val) * k)]
        d.text((160, y + 58), vv, font=font("Bold", 38), fill=INK)
        if k >= 1:
            d.ellipse((W - 190, y + 40, W - 150, y + 80), fill=GREEN)
            d.line((W - 182, y + 60, W - 172, y + 70, W - 158, y + 50), fill=WHITE, width=5)
    k = seg(t, t0 + 4.9, t0 + 5.4)
    if k > 0:
        rounded(d, (130, 1380, W - 130, 1500), 30, tuple(int(LIGHT[j] + (BRAND[j] - LIGHT[j]) * k) for j in range(3)))
        text_center(d, 1416, "Estimer mon bien", font("Bold", 40), WHITE if k > 0.5 else MUTED, 130, W - 130)
    text_center(d, 1640, "Pas de formulaire interminable, pas de rappel commercial.", font("Medium", 32), (207, 224, 255))


def scene_compute(im, t, t0):
    d = ImageDraw.Draw(im)
    text_center(d, 120, "2. Le moteur calcule", font("ExtraBold", 54), WHITE)
    stopwatch(d, t0, t, (W - 300) // 2, 200, final=48 + (t - t0) * 7)
    card(im, (80, 320, W - 80, 1600))
    d = ImageDraw.Draw(im)
    d.text((130, 370), "Créé par des professionnels de l’immobilier", font=font("SemiBold", 28), fill=MUTED)
    for i, (title, sub) in enumerate(STEPS):
        a = t0 + 0.3 + i * 1.25
        k = seg(t, a, a + 1.0)
        if k <= 0:
            continue
        y = 440 + i * 215
        done = k >= 1
        d.ellipse((130, y + 6, 190, y + 66), fill=GREEN if done else LIGHT, outline=GREEN if done else BORDER, width=3)
        if done:
            d.line((147, y + 36, 162, y + 51, 178, y + 24), fill=WHITE, width=6)
        else:
            ang = (t * 360) % 360
            d.arc((140, y + 16, 180, y + 56), ang, ang + 260, fill=BRAND, width=6)
        d.text((220, y), title, font=font("Bold", 36), fill=INK)
        d.text((220, y + 52), sub, font=font("Medium", 27), fill=MUTED)
        rounded(d, (220, y + 110, W - 130, y + 128), 9, LIGHT)
        rounded(d, (220, y + 110, 220 + int((W - 350) * k), y + 128), 9, GREEN if done else BRAND)
    text_center(d, 1680, "Plusieurs modèles croisés, pas une moyenne au doigt mouillé.", font("Medium", 30), (207, 224, 255))


def scene_result(im, t, t0):
    d = ImageDraw.Draw(im)
    text_center(d, 120, "3. Votre estimation", font("ExtraBold", 54), WHITE)
    stopwatch(d, t0, t, (W - 300) // 2, 200, running=False, final=107)
    card(im, (80, 320, W - 80, 1560))
    d = ImageDraw.Draw(im)
    text_center(d, 380, "Valeur estimée", font("SemiBold", 32), MUTED)
    k = seg(t, t0 + 0.1, t0 + 1.6)
    val = int(268000 * k)
    text_center(d, 430, f"{val:,}".replace(",", " ") + " €", font("ExtraBold", 110), BRAND)
    k2 = seg(t, t0 + 1.4, t0 + 2.0)
    if k2 > 0:
        text_center(d, 575, "Fourchette : 252 000 € – 284 000 €", font("Bold", 36), INK)
        rounded(d, (160, 650, W - 160, 674), 12, LIGHT)
        rounded(d, (160 + int((W - 320) * 0.18), 650, 160 + int((W - 320) * (0.18 + 0.64 * k2)), 674), 12, GREEN)
        cx = 160 + int((W - 320) * 0.5)
        d.ellipse((cx - 18, 644, cx + 18, 680), fill=BRAND, outline=WHITE, width=4)
    tiles = [("2 094 €", "prix / m²"), ("36", "ventes analysées"), ("Élevée", "fiabilité"), ("+3,2 %", "marché 12 mois")]
    for i, (v, l) in enumerate(tiles):
        kk = seg(t, t0 + 1.8 + i * 0.2, t0 + 2.2 + i * 0.2)
        if kk <= 0:
            continue
        col, row = i % 2, i // 2
        x = 130 + col * 420
        y = 740 + row * 190
        rounded(d, (x, y, x + 390, y + 160), 26, LIGHT)
        d.text((x + 28, y + 28), v, font=font("ExtraBold", 44), fill=GREEN if v == "Élevée" else INK)
        d.text((x + 28, y + 92), l, font=font("Medium", 28), fill=MUTED)
    k3 = seg(t, t0 + 2.6, t0 + 3.2)
    if k3 > 0:
        d.text((130, 1110), "Pourquoi ce prix ?", font=font("Bold", 34), fill=INK)
        for i, s in enumerate(("Surface et terrain au-dessus de la médiane du secteur", "Bon état général : +4 % vs comparables", "Année 1998 : isolation et DPE dans la norme locale")):
            d.ellipse((134, 1176 + i * 60, 150, 1192 + i * 60), fill=BRAND)
            d.text((170, 1166 + i * 60), s, font=font("Medium", 29), fill=INK)
        mascot(im, "pouce", 230, (W - 350, 1330), alpha=k3)
    text_center(d, 1640, "1 min 47 chrono. Gratuit. Sans engagement.", font("SemiBold", 34), WHITE)


def scene_outro(im, t, t0):
    d = ImageDraw.Draw(im)
    k = seg(t, t0, t0 + 0.7)
    lo = LOGO.copy()
    lo.putalpha(lo.getchannel("A").point(lambda v: int(v * k)))
    im.paste(lo, ((W - lo.width) // 2, 420), lo)
    c = tuple(int(DEEP[j] + (255 - DEEP[j]) * k) for j in range(3))
    text_center(d, 700, "Estimez votre bien", font("ExtraBold", 80), c)
    text_center(d, 800, "gratuitement, en 2 minutes.", font("ExtraBold", 80), c)
    k2 = seg(t, t0 + 0.5, t0 + 1.2)
    if k2 > 0:
        rounded(d, (190, 980, W - 190, 1100), 60, WHITE)
        text_center(d, 1010, "achetemamaison.fr", font("Bold", 50), BRAND)
        text_center(d, 1150, "Disponible sur l’App Store et Google Play", font("Medium", 32), (207, 224, 255))
    mascot(im, "telephone", 560, ((W - 560) // 2, 1240), alpha=k2)


SCENES = [  # (début, fin, rendu)
    (0.0, 3.0, lambda im, t: scene_intro(im, t)),
    (3.0, 9.5, lambda im, t: scene_form(im, t, 3.0)),
    (9.5, 16.5, lambda im, t: scene_compute(im, t, 9.5)),
    (16.5, 21.5, lambda im, t: scene_result(im, t, 16.5)),
    (21.5, 24.5, lambda im, t: scene_outro(im, t, 21.5)),
]


def render_frame(t):
    im = BG.copy()
    for a, b, fn in SCENES:
        if a <= t < b:
            fn(im, t)
            # fondu entre scènes (0,35 s)
            if t - a < 0.35:
                k = 1 - (t - a) / 0.35
                ov = Image.new("RGB", im.size, DEEP)
                im = Image.blend(im, ov, k)
            break
    return im


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total = int(SCENES[-1][1] * FPS)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(total):
        p.stdin.write(render_frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print("->", OUT, os.path.getsize(OUT) // 1024, "Ko", f"{total / FPS:.1f}s")


if __name__ == "__main__":
    main()
