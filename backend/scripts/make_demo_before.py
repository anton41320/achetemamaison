"""One-off: generate a degraded « avant » version of the demo kitchen for the Pack preview (Nano Banana)."""
import asyncio
import base64
import io
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")
sys.path.insert(0, str(ROOT / "backend"))

SRC = ROOT / "frontend" / "assets" / "images" / "demo-after.jpg"
DST = ROOT / "frontend" / "assets" / "images" / "demo-before.jpg"

PROMPT = (
    "Transforme cette photo de cuisine en une photo AMATEUR prise au smartphone AVANT toute retouche, "
    "avec exactement la même pièce, les mêmes meubles, le même point de vue général :\n"
    "- Éclairage terne et jaunâtre, sous-exposé, ombres marquées, balance des blancs chaude et déséquilibrée, léger bruit numérique.\n"
    "- Cadrage légèrement penché (3 à 5 degrés) et verticales non redressées.\n"
    "- Pièce encombrée par des objets du quotidien : vaisselle sale dans l'évier et sur le plan de travail, bouteilles, "
    "torchon, sacs de courses, papiers et courrier, câbles de chargeur, aimants et papiers sur le frigo, une chaise décalée, "
    "un sac poubelle près du meuble, des chaussures au sol.\n"
    "- Surfaces moins nettes, traces sur le sol, ambiance un peu délaissée mais réaliste (pas de dégradation extrême).\n"
    "Le résultat doit rester crédible : c'est la même cuisine, simplement mal photographiée et non rangée. Renvoie uniquement l'image."
)


async def main() -> None:
    from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage
    import photos

    src = SRC.read_bytes()
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"demo-before-{uuid.uuid4()}",
                   system_message="You are a photo editor producing realistic 'before' pictures.")
    chat.with_model("gemini", photos.MODEL).with_params(modalities=["image", "text"])
    msg = UserMessage(text=PROMPT, file_contents=[ImageContent(base64.b64encode(src).decode("utf-8"))])
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise SystemExit("no image returned")
    raw = base64.b64decode(images[0]["data"])
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    ref = Image.open(SRC)
    img = img.resize(ref.size, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=82, optimize=True)
    DST.write_bytes(out.getvalue())
    print("written", DST, len(out.getvalue()), "bytes", img.size)


if __name__ == "__main__":
    asyncio.run(main())
