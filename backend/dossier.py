"""Phase 6 — dynamic sale checklist + document OCR (Gemini 3 Flash) validated by the seller."""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from models import PropertyDoc

OCR_MODEL = "gemini-3-flash-preview"
CURRENT_YEAR = datetime.now(timezone.utc).year

# key -> (label, description, category, validity_months or None)
ITEMS: dict[str, dict] = {
    "titre_propriete": {"label": "Titre de propriété", "category": "obligatoire", "validity_months": None,
                        "description": "Acte notarié prouvant que vous êtes propriétaire. Demandez une copie à votre notaire si besoin."},
    "dpe": {"label": "DPE (diagnostic de performance énergétique)", "category": "obligatoire", "validity_months": 120,
            "description": "Obligatoire dès la mise en annonce. Validité 10 ans (les DPE réalisés avant juillet 2021 ne sont plus valables)."},
    "erp": {"label": "État des risques et pollutions (ERP)", "category": "obligatoire", "validity_months": 6,
            "description": "Risques naturels, miniers, technologiques, radon, pollution des sols. Validité 6 mois."},
    "taxe_fonciere": {"label": "Dernier avis de taxe foncière", "category": "recommande", "validity_months": None,
                      "description": "Demandé par les acquéreurs et le notaire pour le prorata."},
    "amiante": {"label": "Diagnostic amiante", "category": "obligatoire", "validity_months": None,
                "description": "Obligatoire si le permis de construire est antérieur au 1er juillet 1997. Illimité si absence d'amiante."},
    "plomb": {"label": "Constat de risque d'exposition au plomb (CREP)", "category": "obligatoire", "validity_months": None,
              "description": "Obligatoire pour les logements construits avant 1949. Illimité si négatif, 1 an si présence de plomb."},
    "electricite": {"label": "Diagnostic électricité", "category": "obligatoire", "validity_months": 36,
                    "description": "Obligatoire si l'installation a plus de 15 ans. Validité 3 ans."},
    "gaz": {"label": "Diagnostic gaz", "category": "conditionnel", "validity_months": 36,
            "description": "Obligatoire si installation gaz de plus de 15 ans. Validité 3 ans."},
    "termites": {"label": "État parasitaire (termites)", "category": "conditionnel", "validity_months": 6,
                 "description": "Obligatoire si la commune est en zone déclarée par arrêté préfectoral. Validité 6 mois."},
    "merules": {"label": "Information mérules", "category": "conditionnel", "validity_months": None,
                "description": "Information obligatoire si la commune est en zone à risque mérules."},
    "assainissement": {"label": "Contrôle de l'assainissement non collectif", "category": "conditionnel", "validity_months": 36,
                       "description": "Obligatoire si la maison n'est pas raccordée au tout-à-l'égout. Validité 3 ans."},
    "geotechnique": {"label": "Étude géotechnique (G1)", "category": "conditionnel", "validity_months": None,
                     "description": "Pour la vente d'un terrain constructible en zone d'exposition argile moyenne ou forte."},
    "audit_energetique": {"label": "Audit énergétique", "category": "conditionnel", "validity_months": None,
                          "description": "Obligatoire pour les maisons et monopropriétés classées F ou G (E à partir de 2025)."},
    "carnet_logement": {"label": "Carnet d'information du logement (CIL)", "category": "conditionnel", "validity_months": None,
                        "description": "Pour les logements neufs depuis 2023 ou ayant fait l'objet de travaux de rénovation énergétique."},
    "carrez": {"label": "Attestation de surface loi Carrez", "category": "copropriete", "validity_months": None,
               "description": "Obligatoire pour tout lot de copropriété. Illimitée sauf travaux modifiant la surface."},
    "reglement_copro": {"label": "Règlement de copropriété et état descriptif de division", "category": "copropriete", "validity_months": None,
                        "description": "À remettre à l'acquéreur dès la promesse (loi ALUR)."},
    "pv_ag": {"label": "PV des 3 dernières assemblées générales", "category": "copropriete", "validity_months": None,
              "description": "Procès-verbaux des trois dernières AG de copropriété."},
    "pre_etat_date": {"label": "Pré-état daté", "category": "copropriete", "validity_months": None,
                      "description": "Situation financière du lot dans la copropriété, fourni par le syndic."},
    "fiche_synthetique": {"label": "Fiche synthétique de copropriété", "category": "copropriete", "validity_months": None,
                          "description": "Données financières et techniques essentielles de la copropriété."},
    "carnet_entretien": {"label": "Carnet d'entretien de l'immeuble", "category": "copropriete", "validity_months": None,
                         "description": "Tenu par le syndic : travaux réalisés, contrats de maintenance, assurances. À remettre à l'acquéreur (loi ALUR)."},
    "charges_copro": {"label": "Charges des deux derniers exercices", "category": "copropriete", "validity_months": None,
                      "description": "Montant des charges courantes (budget prévisionnel) et hors budget payées par le vendeur sur les deux derniers exercices, "
                                     "et sommes dues au syndicat. Décomptes / appels de fonds du syndic."},
    "dtg": {"label": "Diagnostic technique global (DTG)", "category": "copropriete", "validity_months": None,
            "description": "État général de l'immeuble et travaux à prévoir sur 10 ans. À remettre s'il a été réalisé (immeubles de plus de 15 ans)."},
}


SANITATION_LABELS = {"tout_a_l_egout": "tout-à-l'égout", "fosse_septique": "fosse septique", "fosse_toutes_eaux": "fosse toutes eaux",
                     "microstation": "micro-station"}


def build_checklist(prop: PropertyDoc, risks: Optional[dict] = None) -> list[dict]:
    y = prop.year_built
    maison = prop.property_type == "maison"
    old_install = y is None or y <= CURRENT_YEAR - 15
    flags = (risks or {}).get("dossier_flags") or {}
    items: list[dict] = []

    def add(key: str, required: bool, reason: str):
        items.append({"key": key, **ITEMS[key], "required": required, "reason": reason})

    add("titre_propriete", True, "Toujours requis")
    add("dpe", True, "Toujours requis, dès la publication de l'annonce")
    if risks:
        import georisques
        add("erp", True, "Toujours requis · " + " ".join(georisques.summary_lines(risks))[:400])
    else:
        add("erp", True, "Toujours requis")
    if y is None:
        add("amiante", True, "Année de construction inconnue : requis si permis avant juillet 1997")
        add("plomb", False, "Année inconnue : requis seulement si construit avant 1949")
    else:
        if y < 1997:
            add("amiante", True, f"Construit en {y} (avant juillet 1997)")
        if y < 1949:
            add("plomb", True, f"Construit en {y} (avant 1949)")
    add("electricite", old_install, "Installation probablement de plus de 15 ans" if old_install else "Installation récente : non requis sauf si plus de 15 ans")
    add("gaz", False, "Seulement si installation gaz de plus de 15 ans")
    add("termites", False, "Selon arrêté préfectoral de votre commune")
    add("merules", False, "Selon zone à risque")
    if maison:
        san = getattr(prop.features, "sanitation", None) if getattr(prop, "features", None) else None
        if san == "tout_a_l_egout":
            add("assainissement", False, "Raccordée au tout-à-l'égout : non requis (certificat de raccordement conseillé)")
        elif san in ("fosse_septique", "fosse_toutes_eaux", "microstation"):
            add("assainissement", True, f"Assainissement non collectif ({SANITATION_LABELS[san]}) : contrôle SPANC de moins de 3 ans obligatoire")
        else:
            add("assainissement", False, "Si non raccordée au tout-à-l'égout")
        if flags.get("geotechnique_required"):
            add("geotechnique", True, f"Zone d'exposition argile « {(risks or {}).get('argile', {}).get('label', 'moyenne ou forte').lower()} » (Géorisques)")
        elif prop.land_surface and prop.land_surface > 0:
            add("geotechnique", False, "Terrain : selon zone argile")
    if prop.dpe and prop.dpe.upper() in ("E", "F", "G") and maison:
        add("audit_energetique", True, f"DPE {prop.dpe.upper()} en maison")
    else:
        add("audit_energetique", False, "Requis si DPE E, F ou G (maison / monopropriété)")
    add("carnet_logement", y is not None and y >= 2023, "Logement neuf (2023+)" if y and y >= 2023 else "Si rénovation énergétique depuis 2023")
    if not maison:
        f = prop.features
        add("carrez", True, "Lot de copropriété")
        add("reglement_copro", True, "Lot de copropriété")
        add("pv_ag", True, "Lot de copropriété")
        add("pre_etat_date", True, "Lot de copropriété")
        add("carnet_entretien", True, "Lot de copropriété (loi ALUR)")
        add("charges_copro", True, f"Charges déclarées : {f.condo_fees:g} €/mois, à justifier par les décomptes du syndic"
            if f.condo_fees is not None else "Lot de copropriété (loi ALUR)")
        add("fiche_synthetique", False, "Lot de copropriété (recommandé)")
        old_building = y is None or y <= CURRENT_YEAR - 15
        add("dtg", False, "Immeuble de plus de 15 ans : à joindre s'il existe" if old_building else "Immeuble récent : rarement réalisé")
    add("taxe_fonciere", False, "Recommandé pour le notaire et les acquéreurs")
    return items


def expiry_for(item_key: str, doc_date: Optional[str]) -> Optional[str]:
    months = ITEMS.get(item_key, {}).get("validity_months")
    if not months or not doc_date:
        return None
    try:
        d = date.fromisoformat(doc_date[:10])
    except ValueError:
        return None
    return (d + timedelta(days=int(months * 30.44))).isoformat()


SYSTEM = f"""Tu es un assistant notarial français spécialisé dans les documents de vente immobilière.
Tu lis le document fourni (photo ou PDF) et tu en extrais des informations FACTUELLES, sans jamais inventer.
Si une information n'est pas lisible, mets null. Réponds STRICTEMENT en JSON valide, sans markdown, avec ce schéma :
{{"document_type": one of {list(ITEMS.keys())} or "autre",
 "title": string, "issuer": string|null (diagnostiqueur, notaire, administration…),
 "document_date": "YYYY-MM-DD"|null, "validity_date": "YYYY-MM-DD"|null (si indiquée sur le document),
 "address_found": string|null, "key_fields": [{{"label": string, "value": string}}] (5 à 10 champs clés, ex. classe DPE, résultat, surface, montant, référence),
 "warnings": [string] (mentions importantes : présence d'amiante/plomb, anomalies, document illisible…),
 "summary": string (2 phrases max), "confidence": number 0-1}}"""


def _parse(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    data = json.loads(cleaned[start:end + 1])
    doc_type = data.get("document_type") if data.get("document_type") in ITEMS else "autre"
    return {
        "document_type": doc_type,
        "title": str(data.get("title") or "Document").strip()[:160],
        "issuer": (str(data["issuer"]).strip()[:160] if data.get("issuer") else None),
        "document_date": data.get("document_date") or None,
        "validity_date": data.get("validity_date") or None,
        "address_found": (str(data["address_found"]).strip()[:200] if data.get("address_found") else None),
        "key_fields": [{"label": str(f.get("label", "")).strip()[:80], "value": str(f.get("value", "")).strip()[:200]}
                       for f in (data.get("key_fields") or []) if isinstance(f, dict)][:12],
        "warnings": [str(w).strip()[:200] for w in (data.get("warnings") or [])][:6],
        "summary": str(data.get("summary") or "").strip()[:400],
        "confidence": float(data.get("confidence") or 0.0),
    }


async def ocr_document(data: bytes, mime: str, expected_item: str) -> dict:
    from emergentintegrations.llm.chat import FileContentWithMimeType, LlmChat, UserMessage  # lazy: ~160 MB of SDKs

    suffix = ".pdf" if mime == "application/pdf" else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"ocr-{uuid.uuid4()}", system_message=SYSTEM)
        chat.with_model("gemini", OCR_MODEL)
        expected = ITEMS.get(expected_item, {}).get("label", expected_item)
        text = await chat.send_message(UserMessage(
            text=f"Le vendeur indique qu'il s'agit de : « {expected} ». Vérifie et extrais les informations. Renvoie uniquement le JSON.",
            file_contents=[FileContentWithMimeType(file_path=path, mime_type=mime)]))
        return _parse(text)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
