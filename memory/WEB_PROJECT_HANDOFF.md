# Mise en ligne du site sur achetemamaison.fr — projet web séparé (option B)

## Pourquoi
Les projets « Mobile App » Emergent n'ont pas l'option Domaine personnalisé. Le site web est donc hébergé dans un
**second projet Emergent de type Full Stack App**, qui ne contient **aucune logique métier** : il sert l'export statique
du site et relaie `/api/*` vers le backend unique du projet mobile (`https://estimate-home.emergent.host`).
→ Un seul backend, une seule base, mêmes comptes et mêmes biens sur le site et dans l'application.

## Ce qui est prêt dans ce projet (mobile)
- `webproject/` : kit complet (serveur statique port 3000, passerelle API port 8001, README détaillé).
- `scripts/build-web.sh` génère `backend/web-bundle.zip` (kit + `webdist/`), téléchargeable publiquement :
  `https://estimate-home.emergent.host/api/public/web-bundle.zip` (après « Republier »).
- Testé localement : pages, routes dynamiques, robots, fichier Google, login, upload multipart, fichiers, sitemap
  (les URL du sitemap et les liens des e-mails/Stripe utilisent automatiquement le domaine du site grâce à `X-Forwarded-Host`).

## Marche à suivre (utilisateur)
1. **Republier** ce projet (pour publier le bundle).
2. Écran d'accueil Emergent → nouveau projet **Full Stack App** (nom suggéré : `achetemamaison-web`).
3. Coller le prompt ci-dessous comme premier message.
4. Quand le site est déployé : **Preview → Manage → Domain** → `www.achetemamaison.fr` → créer chez OVH le CNAME indiqué
   (supprimer d'abord la redirection OVH de `www` et les A/AAAA de `www`) ; garder la redirection du domaine nu vers `https://www.achetemamaison.fr`.
5. Revenir ici et dire « domaine actif » : je bascule `EXPO_PUBLIC_SITE_URL` + `robots.txt` vers `https://www.achetemamaison.fr`,
   je régénère le bundle, vous republiez, puis l'agent du projet web re-télécharge le bundle.
6. Google Search Console : ajouter la propriété `https://www.achetemamaison.fr` (le fichier `googlea2db44799c54d4eb.html` est inclus),
   soumettre `api/public/sitemap.xml`.

## Prompt à coller dans le nouveau projet Full Stack App
```
Je veux héberger le site web statique de mon application « Achète ma maison » dans ce projet, sans aucune base de données ni logique métier ici.
Tout le code et les fichiers nécessaires sont dans un bundle public :

  curl -L -o /tmp/web-bundle.zip https://estimate-home.emergent.host/api/public/web-bundle.zip
  unzip -o /tmp/web-bundle.zip -d /tmp/webkit

Lis /tmp/webkit/webproject/README.md et applique-le exactement :
1. Backend (/app/backend, port 8001) : remplace le contenu par /tmp/webkit/webproject/server.py (passerelle qui relaie /api/* vers
   UPSTREAM_API=https://estimate-home.emergent.host), requirements.txt et un .env contenant UPSTREAM_API. N'utilise PAS MongoDB.
2. Frontend (/app/frontend, port 3000) : remplace l'application React par le serveur statique Python /tmp/webkit/webproject/static_server.py
   + webapp.py + le dossier /tmp/webkit/webdist (export statique Expo, ~15 Mo). Démarrage : uvicorn static_server:app --host 0.0.0.0 --port 3000
   (adapte la commande de démarrage du frontend ; si le template exige Node, garde un package.json minimal dont "start" lance cette commande).
3. Vérifie : GET / (page d'accueil), GET /accueil, GET /prix-immobilier/41/cormeray, GET /robots.txt, GET /api/__gateway → {"ok":true},
   GET /api/health (réponse du backend amont), GET /api/public/sitemap.xml (HEAD et GET).
4. Ne modifie pas les fichiers de webdist. Ne crée aucune route métier : tout passe par la passerelle.
5. Prépare le déploiement ; je configurerai ensuite le domaine www.achetemamaison.fr dans Preview → Manage → Domain.
```

## Mise à jour ultérieure du site
Après toute modification du site dans le projet mobile : `scripts/build-web.sh` → Republier (mobile) → dans le projet web :
« re-télécharge https://estimate-home.emergent.host/api/public/web-bundle.zip et remplace webdist/ » → redéployer.
