"""Rapport LLM (Gemini 3 Flash) : interprétation et synthèse uniquement, à partir du JSON calculé. Aucune donnée inventée."""
from __future__ import annotations

import json
import os
import uuid

MODEL = "gemini-3-flash-preview"
SECTIONS = ["resume", "immediat", "voisinage", "nature", "mobilite", "services", "nuisances", "terrain", "risques", "urbanisme", "evolution", "a_verifier"]
SECTION_TITLES = {"resume": "Résumé de l'environnement", "immediat": "Environnement immédiat (0–50 m)", "voisinage": "Voisinage (50–250 m)", "nature": "Nature et espaces verts",
                  "mobilite": "Mobilité et infrastructures", "services": "Services et équipements", "nuisances": "Nuisances potentielles", "terrain": "Relief et caractéristiques du terrain",
                  "risques": "Risques", "urbanisme": "Urbanisme", "evolution": "Évolution potentielle de l'environnement", "a_verifier": "Points à vérifier"}

SYSTEM = (
    "Tu rédiges des analyses factuelles d'environnement immobilier en français. RÈGLES ABSOLUES :\n"
    "1. Tu n'utilises QUE les données du JSON fourni. Tu n'inventes jamais une donnée, un nom, une distance ou un équipement absent du JSON.\n"
    "2. Tu ne calcules rien : toutes les distances, surfaces et comptages sont déjà dans le JSON (champs distance_m, ring, etc.).\n"
    "3. Chaque affirmation importante cite sa source entre crochets : [BD TOPO], [Cadastre], [GPU], [Géorisques], [OSM], [RGE ALTI], [CLC], [BAN].\n"
    "4. Interdiction des jugements catégoriques non mesurés (« quartier calme », « bien ensoleillé », « sans risque »). Formule : "
    "« Une route X est située à environ N m ; les données disponibles ne permettent pas de déterminer le niveau sonore réel. »\n"
    "5. Distingue explicitement : donnée officielle, donnée calculée (distances, densité, pente), interprétation (préfixe « Interprétation : »), "
    "information indisponible (« non disponible dans les sources consultées »), point nécessitant une vérification humaine.\n"
    "6. Pour les risques, distingue toujours : à l'adresse / dans le voisinage / à l'échelle communale. Si risks est null : indique que Géorisques n'a pas pu être consulté.\n"
    "7. Urbanisme : cite le libellé de zone et le nom du règlement, sans interprétation juridique ; rappelle que la collectivité doit confirmer. "
    "Signale les parcelles non bâties proches (nearby_parcels avec built=false) comme facteur d'évolution possible, sans affirmer qu'elles sont constructibles.\n"
    "8. Réponds UNIQUEMENT par un objet JSON avec les clés exactes : " + ", ".join(SECTIONS) + ". Chaque valeur est un texte (2 à 6 phrases, retours à la ligne autorisés) ; "
    "`a_verifier` est une liste de chaînes (3 à 8 points concrets)."
)


def _compact(env: dict) -> dict:
    """Allège le JSON pour le LLM : pas de géométries, listes tronquées."""
    drop = {"geometry"}
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if k not in drop}
        if isinstance(o, list):
            return [clean(x) for x in o]
        return o
    c = clean(env)
    c["neighbours"] = c.get("neighbours", [])[:8]
    c["services"] = c.get("services", [])[:30]
    c["roads"] = c.get("roads", [])[:12]
    c["nearby_parcels"] = [p for p in c.get("nearby_parcels", []) if not p.get("built")][:10] + [p for p in c.get("nearby_parcels", []) if p.get("built")][:4]
    c["sources"] = [{"id": s["id"], "what": s.get("what"), "status": s.get("status"), "fetched_at": s.get("fetched_at")} for s in c.get("sources", [])]
    if c.get("urbanism"):
        c["urbanism"]["documents"] = c["urbanism"]["documents"][:5]
    return c


def _parse(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    start, end = t.find("{"), t.rfind("}")
    data = json.loads(t[start:end + 1])
    out = {}
    for k in SECTIONS:
        v = data.get(k)
        if k == "a_verifier":
            out[k] = [str(x).strip() for x in (v if isinstance(v, list) else [v] if v else []) if str(x).strip()]
        else:
            out[k] = str(v).strip() if v else "Non disponible dans les sources consultées."
    return out


async def generate_report(env: dict) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # lazy

    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"env-{uuid.uuid4()}", system_message=SYSTEM).with_model("gemini", MODEL)
    prompt = ("DONNÉES (seule source autorisée) :\n" + json.dumps(_compact(env), ensure_ascii=False, default=str) +
              "\n\nRédige le rapport structuré en JSON (clés : " + ", ".join(SECTIONS) + ").")
    text = await chat.send_message(UserMessage(text=prompt))
    sections = _parse(text)
    return {"model": MODEL, "sections": sections, "titles": SECTION_TITLES, "order": SECTIONS,
            "disclaimer": "Rapport généré par une IA à partir de données publiques calculées ; il interprète sans mesurer. Les mentions « Interprétation » "
                          "ne sont pas des faits. Vérifiez les points listés auprès des sources et de la collectivité."}
