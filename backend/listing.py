"""AI listing generator (Claude Sonnet 4.6 via emergentintegrations) with a strict no-invention guardrail."""
from __future__ import annotations

import json
import os
import re
import uuid

from models import PropertyDoc

STYLE_GUIDE = {
    "sobre": "Ton sobre, factuel et professionnel. Phrases courtes. Aucun superlatif.",
    "chaleureux": "Ton chaleureux et accueillant, qui aide à se projeter, sans exagération.",
    "premium": "Ton premium et élégant, vocabulaire soigné, mise en valeur de la qualité — sans inventer de prestations.",
    "familial": "Ton familial et rassurant, orienté vie quotidienne (espace, chambres, extérieur si présent).",
}
CONDITION = {"a_renover": "à rénover", "travaux": "travaux à prévoir", "correct": "état correct", "bon": "bon état",
             "neuf_renove": "neuf ou entièrement rénové"}

SYSTEM = """Tu es un rédacteur d'annonces immobilières français. Tu rédiges UNIQUEMENT à partir des faits fournis.
RÈGLES ABSOLUES :
- N'invente JAMAIS une information absente des faits (pas d'étage, ascenseur, parking, balcon, cave, exposition, DPE, école, transport, commerces, calme, luminosité, vue, matériaux…) sauf si elle figure explicitement dans les faits.
- Aucun adjectif sur l'environnement ou le quartier (paisible, calme, recherché, prisé, verdoyant…) : tu ne connais pas les lieux.
- Reprends l'état du bien EXACTEMENT tel que fourni (par ex. « état correct » ne devient jamais « bon état »).
- Si un fait manque, ne le mentionne pas. Ne suppose rien sur le quartier.
- Ne cite pas l'adresse exacte : utilise la commune (et le quartier uniquement s'il est fourni).
- Pas de discrimination, pas de promesse de rendement.
- Réponds STRICTEMENT en JSON valide, sans markdown ni texte autour, avec ce schéma :
{"title": string (≤ 70 caractères), "hook": string (1 phrase d'accroche), "description": string (2 à 4 paragraphes séparés par \\n\\n, 120 à 220 mots), "highlights": [3 à 5 points forts courts, chacun fondé sur un fait fourni]}"""


def _facts(prop: PropertyDoc, include_price: bool, extra: str | None) -> str:
    est = prop.estimation
    lines = [
        f"Type : {'maison' if prop.property_type == 'maison' else 'appartement'}",
        f"Commune : {prop.commune} ({prop.postcode})",
        f"Surface habitable : {prop.surface:g} m²",
        f"Pièces : {prop.rooms} · Chambres : {prop.bedrooms}",
        f"État : {CONDITION.get(prop.condition, prop.condition)}",
    ]
    if prop.year_built:
        lines.append(f"Année de construction : {prop.year_built}")
    if prop.property_type == "maison" and prop.land_surface:
        lines.append(f"Terrain : {prop.land_surface:g} m²")
    if include_price and est:
        lines.append(f"Prix indicatif : fourchette {int(est.low):,} € – {int(est.high):,} € (estimation Achètes ma maison)".replace(",", " "))
    if extra and extra.strip():
        lines.append(f"Précisions fournies par le vendeur (utilisables telles quelles) : {extra.strip()}")
    return "\n".join(lines)


def _parse(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    data = json.loads(cleaned[start:end + 1])
    return {
        "title": str(data.get("title", "")).strip()[:120],
        "hook": str(data.get("hook", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "highlights": [str(h).strip() for h in data.get("highlights", []) if str(h).strip()][:6],
    }


async def generate_listing(prop: PropertyDoc, style: str, extra_facts: str | None, include_price: bool) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # lazy: keeps the LLM SDKs out of API startup memory

    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(api_key=api_key, session_id=f"listing-{uuid.uuid4()}", system_message=SYSTEM).with_model(
        "anthropic", "claude-sonnet-4-6")
    prompt = (f"STYLE : {STYLE_GUIDE[style]}\n\nFAITS (seule source autorisée) :\n{_facts(prop, include_price, extra_facts)}"
              "\n\nRédige l'annonce en français et renvoie uniquement le JSON.")
    text = await chat.send_message(UserMessage(text=prompt))
    return {**_parse(text), "model": "claude-sonnet-4-6"}
