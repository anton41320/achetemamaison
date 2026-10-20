#!/usr/bin/env bash
# Régénère la version Web statique servie par l'API en production (backend/webdist).
# À lancer avant chaque déploiement après une modification du frontend.
set -euo pipefail
cd "$(dirname "$0")/../frontend"
rm -rf ../backend/webdist
npx expo export -p web --output-dir ../backend/webdist
echo "OK : backend/webdist régénéré ($(du -sh ../backend/webdist | cut -f1))"
# Bundle pour le projet web séparé (Full Stack App, domaine achetemamaison.fr) : kit webproject/ + webdist/
cd ..
cp backend/webapp.py webproject/webapp.py
rm -f backend/web-bundle.zip
zip -qr backend/web-bundle.zip webproject -x "webproject/webdist/*" -x "webproject/.env"
(cd backend && zip -qr web-bundle.zip webdist -x "webdist/web-bundle.zip")
echo "OK : backend/web-bundle.zip ($(du -sh backend/web-bundle.zip | cut -f1)) — servi sur /api/public/web-bundle.zip"
