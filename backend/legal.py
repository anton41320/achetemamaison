"""Pages légales publiques servies par l'API (l'app mobile déployée n'héberge pas de front web) :
/api/privacy et /privacy → politique de confidentialité + support, à déclarer dans App Store Connect / Play Console."""
from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse

import auth

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
        "Calculer et expliquer l'estimation de votre bien à partir des ventes immobilières publiques enregistrées et des risques publics (Géorisques).",
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


STYLE = """body{margin:0;background:#F4F7FC;color:#0F1F3D;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.55}
main{max-width:760px;margin:0 auto;padding:32px 20px 64px}h1{font-size:26px;margin:16px 0 4px}.meta{color:#6B7C99;font-size:14px;margin:0 0 20px}
section{background:#fff;border:1px solid #DCE5F2;border-radius:16px;padding:18px 20px;margin:12px 0}h2{font-size:17px;margin:0 0 8px}
p,li{font-size:15px;color:#34486B;margin:6px 0}ul{padding-left:20px;margin:0}.brand{font-weight:700;color:#1656C9;font-size:20px}
a{color:#1656C9}label{display:block;font-weight:600;margin:12px 0 6px}input{width:100%;box-sizing:border-box;padding:12px 14px;border:1px solid #BFCEE6;border-radius:10px;font-size:16px}
button{margin-top:16px;background:#D9342B;color:#fff;border:0;border-radius:10px;padding:14px 20px;font-size:16px;font-weight:700;cursor:pointer}
.ok{background:#E3F4E8;border-color:#2E9E4F}.err{background:#FDE7E5;border-color:#D9342B}"""


def _page(title: str, inner: str) -> str:
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(APP_NAME)} — {escape(title)}</title><style>{STYLE}</style></head><body><main><div class="brand">{escape(APP_NAME)}</div>
<h1>{escape(title)}</h1>{inner}<p class="meta">Contact : <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a> · <a href="privacy">Politique de confidentialité</a></p></main></body></html>"""


def _render() -> str:
    parts = []
    for title, body in SECTIONS:
        items = "".join(f"<li>{escape(p)}</li>" for p in body) if len(body) > 1 else f"<p>{escape(body[0])}</p>"
        parts.append(f"<section><h2>{escape(title)}</h2>{'<ul>' + items + '</ul>' if len(body) > 1 else items}</section>")
    return _page("Politique de confidentialité et support", f'<p class="meta">Dernière mise à jour : {UPDATED}</p>{"".join(parts)}')


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_page():
    return HTMLResponse(_render())


DELETE_FORM = """<section><p>Cette page vous permet de demander la <strong>suppression définitive</strong> de votre compte {app} et de toutes les données associées :
biens, estimations, documents, photos, annonces et achats. Les justificatifs de paiement sont conservés le temps des obligations comptables légales.</p>
<p>Vous pouvez aussi supprimer votre compte directement dans l'application : <em>Mon compte → Supprimer mon compte</em>.</p>
<form method="post" action="delete"><label for="email">Adresse e-mail du compte</label>
<input id="email" name="email" type="email" required placeholder="vous@exemple.fr" autocomplete="email">
<button type="submit">Recevoir le lien de confirmation</button></form>
<p class="meta">Un e-mail contenant un lien de confirmation (valable 15 minutes) sera envoyé si un compte existe pour cette adresse.</p></section>"""


@router.get("/account/delete", response_class=HTMLResponse, include_in_schema=False)
async def delete_form():
    return HTMLResponse(_page("Supprimer mon compte", DELETE_FORM.format(app=escape(APP_NAME))))


@router.post("/account/delete", response_class=HTMLResponse, include_in_schema=False)
async def delete_request(request: Request, email: str = Form(...)):
    origin = f"https://{request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc}"
    await auth.request_web_deletion(email, origin)
    return HTMLResponse(_page("Supprimer mon compte",
                              '<section class="ok"><p><strong>Demande enregistrée.</strong> Si un compte existe pour cette adresse, un e-mail avec un lien de '
                              'confirmation vient d\'être envoyé. Ouvrez-le dans les 15 minutes pour finaliser la suppression.</p></section>'))


@router.get("/account/delete/confirm", response_class=HTMLResponse, include_in_schema=False)
async def delete_confirm(token: str = Query(..., min_length=10)):
    if await auth.confirm_web_deletion(token):
        return HTMLResponse(_page("Compte supprimé", '<section class="ok"><p><strong>Votre compte et vos données ont été supprimés.</strong> '
                                  'Merci d\'avoir utilisé ' + escape(APP_NAME) + '.</p></section>'))
    return HTMLResponse(_page("Lien invalide", '<section class="err"><p>Ce lien de confirmation est invalide ou a expiré. '
                              '<a href="../delete">Refaire une demande</a>.</p></section>'), status_code=400)
