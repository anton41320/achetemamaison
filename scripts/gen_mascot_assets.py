"""Mascotte « Noisette » : recadre chaque visuel autour de l'écureuil et applique un fondu circulaire (alpha)
pour que l'image se fonde dans n'importe quel fond. Sortie : frontend/assets/mascot/noisette-*.webp (alpha).
Entrées : /tmp/mascot/{1756,1767,1768,1769}.png (visuels fournis par l'utilisateur).
Usage : python scripts/gen_mascot_assets.py
"""
import numpy as np
from PIL import Image, ImageFilter

SRC = "/tmp/mascot"
OUT = "/app/frontend/assets/mascot"
SIZE = 560
# nom de sortie -> (fichier source, boîte carrée (x0, y0, x1, y1))
POSES = {
    "pouce": ("1756", (220, 150, 980, 910)),
    "telephone": ("1767", (170, 24, 1110, 964)),
    "noisettes": ("1768", (80, 10, 960, 890)),
    "course": ("1769", (90, 20, 1030, 960)),
}


def radial_alpha(size: int, inner: float = 0.58, outer: float = 0.98) -> Image.Image:
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    c = (size - 1) / 2
    r = np.sqrt((x - c) ** 2 + (y - c) ** 2) / c
    a = np.clip((outer - r) / (outer - inner), 0, 1)
    a = a * a * (3 - 2 * a)  # smoothstep : fondu doux
    return Image.fromarray((a * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2))


def main() -> None:
    import os
    os.makedirs(OUT, exist_ok=True)
    alpha = radial_alpha(SIZE)
    for name, (src, box) in POSES.items():
        im = Image.open(f"{SRC}/{src}.png").convert("RGB").crop(box).resize((SIZE, SIZE), Image.LANCZOS)
        im.putalpha(alpha)
        path = f"{OUT}/noisette-{name}.webp"
        im.save(path, "WEBP", quality=82, method=6)
        print("->", path, os.path.getsize(path) // 1024, "Ko")


if __name__ == "__main__":
    main()
