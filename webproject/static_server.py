"""Projet web « Achète ma maison » (Full Stack App Emergent) — serveur du site statique, port 3000.

Sert l'export statique Expo (`webdist/`, généré par le projet mobile) avec la résolution des routes dynamiques
(`/prix-immobilier/[dept]/[commune]`), le fichier de vérification Google et les en-têtes de cache.
Lancement : `uvicorn static_server:app --host 0.0.0.0 --port 3000`
"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from webapp import mount_web

load_dotenv()
app = FastAPI(title="Achète ma maison — site web", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/__health", include_in_schema=False)
async def health():
    return {"ok": True}


if not mount_web(app, Path(__file__).parent / "webdist"):
    raise SystemExit("webdist/ introuvable : récupérez le bundle (voir README.md)")
