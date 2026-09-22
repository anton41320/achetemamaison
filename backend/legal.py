"""Pages légales publiques servies par l'API (l'app mobile déployée n'héberge pas de front web) :
/api/privacy et /privacy → politique de confidentialité + support, à déclarer dans App Store Connect / Play Console."""
from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

APP_NAME = "Achètes ma maison"
SUPPORT_EMAIL = "contact@achetesmamaison.fr"
UPDATED = "17 septembre 2026"

SECTIONS: list[tuple[str, list[str]]] = [
    ("1. Qui sommes-nous ?", [
        f"{APP_NAME} est une application destinée aux particuliers qui souhaitent estimer puis préparer la vente de leur logement. "
        f"L'éditeur de l'application est responsable du traitement de vos données. Contact : {SUPPORT_EMAIL}."]),
    ("2. Données que nous collectons", [
        "Compte : adresse e-mail et mot de passe (stocké uniquement sous forme hachée).",
        "Biens : adresse du logement, caractéristiques déclarées (surface, pièces, état, équipements…), prix cible éventuel.",
        "Documents et photos que vous importez volontairement (diagnostics, titre de propriété, photos du bien).",
        "Achats : référence de commande et e-mail de reçu transmis par notre prestataire de paiement (Stripe sur le web, Apple/Google "
        "sur mobile). Aucun numéro de carte n'est stocké par l'application.",
        "Données techniques nécessaires au fonctionnement (journaux serveur, jeton de session)."]),
    ("3. Pourquoi nous les utilisons", [
        "Calculer et expliquer l'estimation de votre bien à partir des ventes publiques (base DVF de l'État) et des risques publics (Géorisques).",
        "Constituer votre dossier de vente : checklist, lecture automatique des documents, rappels d'expiration, export pour le notaire.",
        "Fournir les outils IA du Pack premium (rédaction d'annonce, retouche photo, lecture de documents).",
        "Assurer le paiement, l'envoi de votre reçu et la gestion de votre compte (réinitialisation du mot de passe)."]),
    ("4. Intelligence artificielle", [
        "Les textes d'annonce, retouches photo et lectures de documents sont produits par des modèles d'IA tiers hébergés hors de l'appareil. "
        "Seuls les éléments nécessaires (faits déclarés, photo ou document concerné) leur sont transmis, sans votre adresse e-mail. "
        "Les résultats sont des propositions : vous les vérifiez et les validez avant toute utilisation. Les visuels retouchés portent la mention « non contractuel »."]),
    ("5. Partage et sous-traitants", [
        "Vos données ne sont ni vendues ni louées. Elles sont traitées par nos prestataires techniques strictement pour les finalités ci-dessus : "
        "hébergement et base de données, stockage des fichiers, paiement, envoi d'e-mails, fournisseurs de modèles d'IA, géocodage des adresses (Base Adresse Nationale)."]),
    ("6. Durée de conservation", [
        "Vos données sont conservées tant que votre compte est actif. La suppression du compte depuis l'écran « Mon compte » efface vos biens, documents, "
        "photos et annonces ; les justificatifs de paiement sont conservés le temps des obligations comptables légales."]),
    ("7. Vos droits", [
        "Conformément au RGPD, vous disposez d'un droit d'accès, de rectification, d'effacement, de limitation et de portabilité. Vous pouvez supprimer "
        "votre compte à tout moment dans l'application ou nous écrire à l'adresse ci-dessous. Vous pouvez également saisir la CNIL (cnil.fr)."]),
    ("8. Sécurité", [
        "Connexions chiffrées (HTTPS), mots de passe hachés, jetons de session à durée limitée, accès aux fichiers réservé au propriétaire du compte."]),
    ("9. Support", [
        f"Une question, un problème ou une demande concernant vos données : écrivez-nous à {SUPPORT_EMAIL}. Nous répondons sous 72 heures ouvrées."]),
]


def _render() -> str:
    parts = []
    for title, body in SECTIONS:
        items = "".join(f"<li>{escape(p)}</li>" for p in body) if len(body) > 1 else f"<p>{escape(body[0])}</p>"
        parts.append(f"<section><h2>{escape(title)}</h2>{'<ul>' + items + '</ul>' if len(body) > 1 else items}</section>")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(APP_NAME)} — Politique de confidentialité et support</title>
<style>body{{margin:0;background:#F4F7FC;color:#0F1F3D;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.55}}
main{{max-width:760px;margin:0 auto;padding:32px 20px 64px}}h1{{font-size:26px;margin:16px 0 4px}}.meta{{color:#6B7C99;font-size:14px;margin:0 0 20px}}
section{{background:#fff;border:1px solid #DCE5F2;border-radius:16px;padding:18px 20px;margin:12px 0}}h2{{font-size:17px;margin:0 0 8px}}
p,li{{font-size:15px;color:#34486B;margin:6px 0}}ul{{padding-left:20px;margin:0}}.brand{{font-weight:700;color:#1656C9;font-size:20px}}
a{{color:#1656C9}}</style></head><body><main><div class="brand">{escape(APP_NAME)}</div>
<h1>Politique de confidentialité et support</h1><p class="meta">Dernière mise à jour : {UPDATED}</p>{''.join(parts)}
<p class="meta">Contact : <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p></main></body></html>"""


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_page():
    return HTMLResponse(_render())
