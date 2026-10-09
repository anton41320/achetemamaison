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
CONDITION = {"a_renover": "à rénover", "travaux": "travaux à prévoir", "correct": "état correct", "bon": "bon état", "tres_bon": "très bon état",
             "neuf_renove": "neuf ou entièrement rénové"}
FIREPLACE_LABELS = {"aucune": "aucune", "insert": "cheminée avec insert", "foyer_ouvert": "cheminée à foyer ouvert",
                    "poele_bois": "poêle à bois", "poele_granules": "poêle à granulés"}
PARKING_LABELS = {"aucun": "aucun", "exterieur": "place extérieure", "interieur": "place intérieure / box", "garage": "garage fermé"}

SYSTEM = """Tu es un rédacteur d'annonces immobilières français. Tu rédiges UNIQUEMENT à partir des faits fournis.
RÈGLES ABSOLUES :
- N'invente JAMAIS une information absente des faits (pas d'étage, ascenseur, parking, balcon, cave, exposition, DPE, école, transport, commerces, calme, luminosité, vue, matériaux…) sauf si elle figure explicitement dans les faits.
- Aucun adjectif sur l'environnement ou le quartier (paisible, calme, recherché, prisé, verdoyant…) : tu ne connais pas les lieux.
- Si un bloc « ATOUTS DU QUARTIER MESURÉS » est fourni, tu peux citer ces éléments (tous ou une partie), avec leur distance exacte telle qu'indiquée (ex. « école à environ 300 m »), sans les qualifier ni en ajouter. Aucun jugement sur le cadre (remarquable, exceptionnel, privilégié, agréable, « à deux pas »…). Sans ce bloc, ne parle pas du quartier.
- Reprends l'état du bien EXACTEMENT tel que fourni (par ex. « état correct » ne devient jamais « bon état »).
- Si un fait manque, ne le mentionne pas. Ne suppose rien sur le quartier.
- Ne cite pas l'adresse exacte : utilise la commune (et le quartier uniquement s'il est fourni).
- Pas de discrimination, pas de promesse de rendement.
- Réponds STRICTEMENT en JSON valide, sans markdown ni texte autour, avec ce schéma :
{"title": string (≤ 70 caractères), "hook": string (1 phrase d'accroche), "description": string (2 à 4 paragraphes séparés par \\n\\n, 120 à 220 mots), "highlights": [3 à 5 points forts courts, chacun fondé sur un fait fourni]}"""


def _facts(prop: PropertyDoc, include_price: bool, extra: str | None, env_block: str | None = None) -> str:
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
    san = getattr(getattr(prop, "features", None), "sanitation", None)
    if prop.property_type == "maison" and san:
        from dossier import SANITATION_LABELS

        lines.append(f"Assainissement : {SANITATION_LABELS.get(san, san)}")
    f = prop.features
    if prop.property_type == "maison" and f.outbuilding:
        from estimator import OUTBUILDING_LABELS

        lines.append("Dépendance : " + OUTBUILDING_LABELS.get(f.outbuilding_type or "", "dépendance").lower() + (f" de {f.outbuilding_surface:g} m²" if f.outbuilding_surface else ""))
    if f.fireplace and f.fireplace != "aucune":
        lines.append(f"Chauffage d'appoint / cheminée : {FIREPLACE_LABELS[f.fireplace]}")
    if prop.property_type == "appartement":
        if f.floor is not None:
            lines.append(f"Étage : {'rez-de-chaussée' if f.floor == 0 else f'{f.floor}e'}" + (" (dernier étage)" if f.top_floor and f.floor > 0 else "")
                         + ("" if f.elevator is None else f" · ascenseur : {'oui' if f.elevator else 'non'}"))
        if f.parking:
            lines.append(f"Stationnement : {PARKING_LABELS[f.parking]}")
        if f.caretaker is not None:
            lines.append(f"Gardien / concierge : {'oui' if f.caretaker else 'non'}")
        if f.condo_fees is not None:
            lines.append(f"Charges de copropriété : {f.condo_fees:g} €/mois")
        heat = [x for x in (f.heating_mode and f"chauffage {f.heating_mode}", f.underfloor_heating and "chauffage au sol") if x]
        if heat:
            lines.append("Chauffage : " + ", ".join(heat))
    if include_price and prop.target_price:
        lines.append(f"Prix de vente : {int(prop.target_price):,} € — prix fixé par le vendeur : l'annonce affiche exactement ce montant "
                     "(jamais de fourchette, jamais le mot « estimation »).".replace(",", " "))
    elif include_price and est:
        lines.append(f"Prix indicatif : fourchette {int(est.low):,} € – {int(est.high):,} € (estimation Achète ma maison)".replace(",", " "))
    if extra and extra.strip():
        lines.append(f"Précisions fournies par le vendeur (utilisables telles quelles) : {extra.strip()}")
    if env_block:
        lines.append("\n" + env_block)
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


HEADLINE_SEPARATOR = "." * 59


def _fmt_land(m2: float) -> str:
    if m2 >= 10_000:
        ha = m2 / 10_000
        s = f"{ha:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"Terrain {s} Hectare{'s' if ha >= 2 else ''}"
    return f"Terrain {m2:g} m²".replace(".", ",")


def headline(prop: PropertyDoc) -> str:
    """Ligne d'accroche structurée, construite uniquement à partir des faits saisis (jamais par l'IA).

    Ex. « 41200 - Villefranche-sur-Cher - Propriété 6 pièces 185 m² - 4 chambres - Garage - Dépendance - Piscine - Terrain 1,3 Hectare »."""
    f = prop.features
    maison = prop.property_type == "maison"
    land = prop.land_surface if maison else None
    kind = "Appartement" if not maison else ("Propriété" if (land or 0) >= 5000 else "Maison")
    surface = f"{prop.surface:g}".replace(".", ",")
    parts = [prop.postcode, prop.commune, f"{kind} {prop.rooms} pièce{'s' if prop.rooms > 1 else ''} {surface} m²"]
    if prop.bedrooms:
        parts.append(f"{prop.bedrooms} chambre{'s' if prop.bedrooms > 1 else ''}")
    if maison:
        if f.single_storey:
            parts.append("Plain-pied")
        if f.master_suite:
            parts.append("Suite parentale")
        if f.garage == "un":
            parts.append("Garage")
        elif f.garage == "deux_plus":
            parts.append("Garages")
        if f.outbuilding:
            from estimator import OUTBUILDING_LABELS

            parts.append(OUTBUILDING_LABELS.get(f.outbuilding_type or "", "Dépendance"))
        if f.pool and f.pool != "aucune":
            parts.append("Piscine")
        if f.terrace:
            parts.append("Terrasse")
        if f.basement:
            parts.append("Sous-sol")
        if f.convertible_attic:
            parts.append("Combles aménageables")
        if land:
            parts.append(_fmt_land(land))
    else:
        if f.floor is not None:
            parts.append("Rez-de-chaussée" if f.floor == 0 else ("Dernier étage" if f.top_floor else f"{f.floor}e étage") + (" avec ascenseur" if f.elevator else ""))
        if f.balcony:
            parts.append("Balcon")
        if f.terrace:
            parts.append("Terrasse")
        if f.parking and f.parking != "aucun":
            parts.append({"exterieur": "Parking", "interieur": "Box", "garage": "Garage"}[f.parking])
        if f.cellar:
            parts.append("Cave")
    if f.fireplace in ("poele_bois", "poele_granules"):
        parts.append("Poêle")
    elif f.fireplace in ("insert", "foyer_ouvert"):
        parts.append("Cheminée")
    if f.dpe:
        parts.append(f"DPE {f.dpe}")
    return " - ".join(parts)


async def generate_listing(prop: PropertyDoc, style: str, extra_facts: str | None, include_price: bool, env: dict | None = None) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # lazy: keeps the LLM SDKs out of API startup memory

    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(api_key=api_key, session_id=f"listing-{uuid.uuid4()}", system_message=SYSTEM).with_model(
        "anthropic", "claude-sonnet-4-6")
    from environment.listing_facts import facts_block

    env_block = facts_block(env) if env else None
    prompt = (f"STYLE : {STYLE_GUIDE[style]}\n\nFAITS (seule source autorisée) :\n{_facts(prop, include_price, extra_facts, env_block)}"
              "\n\nRédige l'annonce en français et renvoie uniquement le JSON.")
    text = await chat.send_message(UserMessage(text=prompt))
    return {**_parse(text), "headline": headline(prop), "model": "claude-sonnet-4-6", "used_environment": bool(env_block)}
