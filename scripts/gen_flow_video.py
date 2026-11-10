"""Vidéo verticale (1080×1920, 30 i/s, ~31 s) assemblée à partir des VRAIES captures du site (scripts/capture_estimation_flow.py).
Usage : python scripts/gen_flow_video.py  ->  /app/backend/media/estimation-parcours.mp4
"""
import os
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SHOTS = "/tmp/realshots"
FONTS = "/app/frontend/assets/fonts"
ASSETS = "/app/frontend/assets"
OUT = "/app/backend/media/estimation-parcours.mp4"
DEEP, BRAND, WHITE, PALE, GREEN = (11, 59, 143), (22, 86, 201), (255, 255, 255), (207, 224, 255), (30, 158, 106)
PH_W, PH_H, PH_X, PH_Y, PH_R = 720, 1558, (W - 720) // 2, 330, 56
FADE = 0.4

# (début, capture, titre, sous-titre)
SCENES = [
    (0.0, "01-landing", "Sur achetemamaison.fr", "Estimation gratuite, sans compte"),
    (3.0, "02-step1-empty", "Étape 1 · Votre adresse", "Partout en France"),
    (5.5, "03-step1-typing", "Étape 1 · Votre adresse", "Vous tapez, on cherche"),
    (7.5, "04-step1-results", "Adresse géolocalisée", "Base Adresse Nationale"),
    (9.5, "05-step1-selected", "Adresse reconnue ✓", "On passe à la suite"),
    (11.5, "06-step2-empty", "Étape 2 · Le bien", "Maison ou appartement"),
    (13.5, "07-step2-filled", "Étape 2 · Le bien", "Surface, pièces, chambres"),
    (16.0, "08-step3-filled", "Étape 3 · Quelques détails", "Année, état général, terrain"),
    (19.0, "09-step4", "Étape 4 · Équipements", "Optionnel, mais ça affine le prix"),
    (21.5, "10-loading", "Calcul en cours…", "Ventes réelles autour du bien"),
    (23.0, "11-result", "Résultat : 249 000 €", "Fourchette 237 000 – 262 000 € · en 1,3 s"),
    (27.0, "13-mascot", "Noisette vous guide", "De l'estimation jusqu'à la vente"),
    (29.0, None, "Estimez votre bien gratuitement", "achetemamaison.fr"),
]
END = 31.5


def font(name, size):
    return ImageFont.truetype(f"{FONTS}/PlusJakartaSans-{name}.ttf", size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


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
MASCOT = Image.open(f"{ASSETS}/mascot/noisette-pouce.webp").convert("RGBA").resize((520, 520))
SHOT_IMGS = {s[1]: Image.open(f"{SHOTS}/{s[1]}.png").convert("RGB") for s in SCENES if s[1]}
MASK = Image.new("L", (PH_W, PH_H), 0)
ImageDraw.Draw(MASK).rounded_rectangle((0, 0, PH_W - 1, PH_H - 1), radius=PH_R, fill=255)

# Cadre téléphone + ombre, rendu une fois
FRAME = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(_sh).rounded_rectangle((PH_X - 14, PH_Y + 10, PH_X + PH_W + 14, PH_Y + PH_H + 40), radius=PH_R + 14, fill=(0, 0, 0, 110))
FRAME = Image.alpha_composite(FRAME, _sh.filter(ImageFilter.GaussianBlur(30)))
ImageDraw.Draw(FRAME).rounded_rectangle((PH_X - 14, PH_Y - 14, PH_X + PH_W + 14, PH_Y + PH_H + 14), radius=PH_R + 14, fill=(20, 24, 34, 255))


def screen(shot, k):
    """Capture à l'échelle de l'écran, avec un très léger zoom (Ken Burns) selon k∈[0,1]."""
    im = SHOT_IMGS[shot]
    z = 1.0 + 0.025 * k
    cw, ch = int(im.width / z), int(im.height / z)
    cx, cy = (im.width - cw) // 2, int((im.height - ch) * 0.3)
    return im.crop((cx, cy, cx + cw, cy + ch)).resize((PH_W, PH_H), Image.BILINEAR)


def compose(shot, k):
    im = BG.copy()
    if shot:
        im.paste(FRAME, (0, 0), FRAME)
        im.paste(screen(shot, k), (PH_X, PH_Y), MASK)
    return im


def caption(im, title, sub, alpha):
    d = ImageDraw.Draw(im)
    f1, f2 = font("ExtraBold", 60), font("SemiBold", 34)
    c1 = tuple(int(DEEP[j] + (255 - DEEP[j]) * alpha) for j in range(3))
    c2 = tuple(int(DEEP[j] + (PALE[j] - DEEP[j]) * alpha) for j in range(3))
    w = d.textlength(title, font=f1)
    d.text(((W - w) / 2, 120), title, font=f1, fill=c1)
    w = d.textlength(sub, font=f2)
    d.text(((W - w) / 2, 206), sub, font=f2, fill=c2)


def end_card(im, k):
    d = ImageDraw.Draw(im)
    lo = LOGO.copy()
    lo.putalpha(lo.getchannel("A").point(lambda v: int(v * k)))
    im.paste(lo, ((W - lo.width) // 2, 560), lo)
    c = tuple(int(DEEP[j] + (255 - DEEP[j]) * k) for j in range(3))
    for i, line in enumerate(("Estimez votre bien", "gratuitement, en 2 minutes.")):
        f = font("ExtraBold", 76)
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, 800 + i * 96), line, font=f, fill=c)
    if k > 0.3:
        d.rounded_rectangle((190, 1060, W - 190, 1180), radius=60, fill=WHITE)
        f = font("Bold", 50)
        w = d.textlength("achetemamaison.fr", font=f)
        d.text(((W - w) / 2, 1090), "achetemamaison.fr", font=f, fill=BRAND)
        f = font("Medium", 32)
        s = "Gratuit · sans inscription · App Store & Google Play"
        w = d.textlength(s, font=f)
        d.text(((W - w) / 2, 1230), s, font=f, fill=PALE)
    m = MASCOT.copy()
    m.putalpha(m.getchannel("A").point(lambda v: int(v * k)))
    im.paste(m, ((W - 520) // 2, 1320), m)


def scene_at(t):
    idx = 0
    for i, s in enumerate(SCENES):
        if t >= s[0]:
            idx = i
    return idx


def render_frame(t):
    i = scene_at(t)
    start, shot, title, sub = SCENES[i]
    end = SCENES[i + 1][0] if i + 1 < len(SCENES) else END
    k = (t - start) / max(end - start, 0.01)
    if shot is None:
        im = BG.copy()
        end_card(im, ease((t - start) / 0.8))
    else:
        im = compose(shot, k)
    # fondu enchaîné avec la scène précédente
    if i > 0 and t - start < FADE:
        pstart, pshot = SCENES[i - 1][0], SCENES[i - 1][1]
        prev = compose(pshot, 1.0) if pshot else BG.copy()
        im = Image.blend(prev, im, ease((t - start) / FADE))
    if shot is not None:
        a = ease((t - start) / 0.35) if i > 0 else ease((t - start) / 0.8)
        caption(im, title, sub, a)
    return im


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    total = int(END * FPS)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for n in range(total):
        p.stdin.write(render_frame(n / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print("->", OUT, os.path.getsize(OUT) // 1024, "Ko", f"{END:.1f}s")


if __name__ == "__main__":
    main()
