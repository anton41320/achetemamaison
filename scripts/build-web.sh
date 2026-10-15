#!/usr/bin/env bash
# Régénère la version Web statique servie par l'API en production (backend/webdist).
# À lancer avant chaque déploiement après une modification du frontend.
set -euo pipefail
cd "$(dirname "$0")/../frontend"
rm -rf ../backend/webdist
npx expo export -p web --output-dir ../backend/webdist
echo "OK : backend/webdist régénéré ($(du -sh ../backend/webdist | cut -f1))"
