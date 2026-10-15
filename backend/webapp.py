"""Sert la version Web (export statique Expo, `expo export -p web`) depuis l'API.

Sur l'hôte déployé, la racine du domaine est servie par l'API : on y sert donc le site Web pré-rendu (pages publiques SEO +
application). Le dossier `backend/webdist/` est produit par `cd frontend && npx expo export -p web --output-dir ../backend/webdist`
et versionné avec le code : il doit être régénéré avant chaque déploiement (voir memory/PRD.md).

Résolution d'une URL : fichier exact → `chemin.html` → `chemin/index.html` → route dynamique (`[param].html`, les crochets
acceptent n'importe quel segment) → `+not-found.html` (ou `index.html`, l'application Expo Router prend alors le relais côté client).
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEBDIST = Path(__file__).parent / "webdist"
HTML_HEADERS = {"Cache-Control": "no-cache"}  # le HTML référence des bundles hashés : il ne doit pas être mis en cache


def _html_routes(dist: Path) -> list[tuple[list[str], Path]]:
    routes = []
    for p in dist.rglob("*.html"):
        rel = p.relative_to(dist).with_suffix("")
        segs = [s for s in rel.as_posix().split("/") if s]
        if segs and segs[-1] == "index":
            segs = segs[:-1]
        routes.append((segs, p))
    # les routes statiques d'abord, puis les dynamiques les plus spécifiques (moins de segments variables)
    routes.sort(key=lambda r: (sum(1 for s in r[0] if s.startswith("[")), -len(r[0])))
    return routes


def mount_web(app: FastAPI, dist: Path = WEBDIST) -> bool:
    if not (dist / "index.html").exists():
        return False
    routes = _html_routes(dist)
    not_found = dist / "+not-found.html"
    for sub in ("_expo", "assets"):
        if (dist / sub).is_dir():
            app.mount(f"/{sub}", StaticFiles(directory=dist / sub), name=f"web-{sub}")

    def resolve(path: str) -> Path:
        clean = path.strip("/")
        if clean:
            candidate = (dist / clean).resolve()
            if dist.resolve() in candidate.parents and candidate.is_file():
                return candidate
        segs = [s for s in clean.split("/") if s]
        for pattern, file in routes:
            if len(pattern) == len(segs) and all(p.startswith("[") or p == s for p, s in zip(pattern, segs)):
                return file
        return not_found if not_found.exists() else dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def web_catch_all(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not Found")
        file = resolve(full_path)
        headers = HTML_HEADERS if file.suffix == ".html" else {"Cache-Control": "public, max-age=31536000, immutable" if "/_expo/" in file.as_posix() else "public, max-age=3600"}
        return FileResponse(file, headers=headers, status_code=404 if file == not_found else 200)

    return True
