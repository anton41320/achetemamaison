"""Projet web « Achète ma maison » (Full Stack App Emergent) — passerelle API, port 8001.

Le site web appelle `/api/*` sur sa propre origine ; cette passerelle transmet chaque requête, telle quelle, au backend
unique du projet mobile (UPSTREAM_API, ex. https://estimate-home.emergent.host) : mêmes comptes, mêmes biens, même base
de données, aucun service dupliqué. Fichiers (photos, documents, PDF) et envois multipart sont relayés en flux.
Lancement : `uvicorn server:app --host 0.0.0.0 --port 8001`
"""
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

load_dotenv()
UPSTREAM = os.environ.get("UPSTREAM_API", "https://estimate-home.emergent.host").rstrip("/")
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length"}

app = FastAPI(title="Achète ma maison — passerelle API", docs_url=None, redoc_url=None, openapi_url=None)
client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0), follow_redirects=False)


@app.on_event("shutdown")
async def _close():
    await client.aclose()


@app.get("/api/__gateway", include_in_schema=False)
async def gateway_health():
    return {"ok": True, "upstream": UPSTREAM}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], include_in_schema=False)
async def proxy(path: str, request: Request):
    url = f"{UPSTREAM}/api/{path}"
    if request.url.query:
        url += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    # Le backend amont construit les liens absolus (e-mails, sitemap, Stripe) à partir de l'hôte public du site.
    headers["x-forwarded-host"] = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    headers["x-forwarded-proto"] = request.headers.get("x-forwarded-proto", "https")
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")
    if client_ip:
        headers["x-forwarded-for"] = client_ip
    # Corps lu en entier avant transfert : l'amont reçoit un Content-Length (pas de « chunked »), ce qui évite les coupures
    # (erreurs 520) sur les envois de photos/documents depuis mobile. Taille bornée côté backend.
    body = await request.body() if request.method in {"POST", "PUT", "PATCH", "DELETE"} else None
    try:
        upstream_req = client.build_request(request.method, url, headers=headers, content=body)
        upstream = await client.send(upstream_req, stream=True)
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=503, content={"detail": f"Serveur momentanément indisponible ({type(exc).__name__}). Réessayez dans un instant."})
    resp_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
    return StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code, headers=resp_headers, background=BackgroundTask(upstream.aclose))
