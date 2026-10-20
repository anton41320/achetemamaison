# Achète ma maison — projet web (Full Stack App Emergent)

Ce dossier est un **kit prêt à l'emploi** pour héberger le site web `achetemamaison.fr` dans un projet Emergent
« Full Stack App » (qui propose l'option Domaine personnalisé), **sans dupliquer le backend ni la base de données** :

```
Navigateur ──► www.achetemamaison.fr
                 ├─ /            → static_server.py (port 3000) : export statique Expo (webdist/)
                 └─ /api/*       → server.py (port 8001) : passerelle vers https://estimate-home.emergent.host/api/*
                                                            (backend unique du projet mobile : comptes, biens, Stripe, IA…)
```

## Contenu
| Fichier | Rôle |
|---|---|
| `static_server.py` | FastAPI qui sert `webdist/` (routes dynamiques, Google verification, cache) — port 3000 |
| `server.py` | FastAPI passerelle `/api/*` → backend du projet mobile — port 8001 |
| `webapp.py` | Logique de service des fichiers statiques (copie de `backend/webapp.py` du projet mobile) |
| `requirements.txt` | fastapi, uvicorn, httpx, python-dotenv |
| `.env.example` | `UPSTREAM_API` (backend amont), `GOOGLE_SITE_VERIFICATION` |
| `webdist/` | **À récupérer** : export statique du site (≈ 15 Mo), voir ci-dessous |

## Récupérer l'export statique (`webdist/`)
Le projet mobile publie le bundle complet (ce kit + `webdist/`) à l'adresse :

```
https://estimate-home.emergent.host/api/public/web-bundle.zip
```

```bash
curl -L -o /tmp/web-bundle.zip https://estimate-home.emergent.host/api/public/web-bundle.zip
unzip -o /tmp/web-bundle.zip -d /app/webkit
```

À chaque mise à jour du site côté projet mobile (puis « Republier »), re-télécharger le bundle et redéployer ce projet.

## Mise en place dans le projet Full Stack (pour l'agent du nouveau projet)
1. Backend (`/app/backend`) : remplacer le contenu par `server.py`, `requirements.txt`, `.env` (copie de `.env.example`).
   Ne PAS connecter de MongoDB : ce backend ne stocke rien.
2. Frontend (`/app/frontend`) : remplacer l'app React par le serveur statique : `static_server.py` + `webapp.py` + `webdist/`,
   démarré par `uvicorn static_server:app --host 0.0.0.0 --port 3000` (adapter la commande de démarrage du frontend dans supervisor /
   le `package.json` : `"start": "python3 -m uvicorn static_server:app --host 0.0.0.0 --port 3000"` si le template exige Node).
3. Vérifier : `GET /` → page d'accueil (`accueil.html` est la vitrine : `/accueil`), `GET /api/__gateway` → `{"ok": true}`,
   `GET /api/health` → réponse du backend amont, `GET /robots.txt`, `GET /api/public/sitemap.xml`.
4. Déployer, puis **Preview → Manage → Domain** : ajouter `www.achetemamaison.fr`, créer le CNAME indiqué chez OVH, attendre la vérification.
5. Prévenir le projet mobile pour basculer l'adresse officielle (`EXPO_PUBLIC_SITE_URL=https://www.achetemamaison.fr`), régénérer le bundle,
   puis re-télécharger `webdist/` ici.

## Points d'attention
- Les URL de retour Stripe et les liens des e-mails sont construits par le backend amont à partir de l'en-tête `X-Forwarded-Host`
  transmis par la passerelle : ils pointeront bien vers `achetemamaison.fr`.
- Les webhooks Stripe restent configurés sur le backend amont (inchangé).
- Le site appelle `/api` sur sa propre origine (`window.location.origin`) : aucune variable à changer côté front.
