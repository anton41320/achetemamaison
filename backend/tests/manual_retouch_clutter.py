"""Test manuel : retouche d'une photo très encombrée (affiches avec texte, instruments) — le contrôle de fidélité ne doit plus
bloquer sur les détails fins des posters. Usage : python tests/manual_retouch_clutter.py [chemin_image]"""
import asyncio
import base64
import os
import sys

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")


async def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        raw = open(src, "rb").read()
    else:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id="test-clutter", system_message="Photographe")
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        _, images = await chat.send_message_multimodal_response(UserMessage(
            text="Photo réaliste prise au smartphone d'un salon de pavillon français encombré : murs couverts d'affiches de concerts "
                 "avec des textes lisibles et des logos, une batterie, un clavier, une guitare, une table basse avec bouteilles, un "
                 "emballage plastique imprimé au sol, canapé gris, télévision. Lumière du jour moyenne, format 4:3."))
        raw = base64.b64decode(images[0]["data"])
        open("/tmp/clutter.png", "wb").write(raw)
    import photos

    try:
        out, mime = await photos.retouch(raw)
        open("/tmp/clutter_out.jpg", "wb").write(out)
        print("RETOUCH OK", len(out), mime)
    except photos.UnfaithfulRetouch as e:
        print("REFUSED:", e)


asyncio.run(main())
