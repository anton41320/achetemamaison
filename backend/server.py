from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

import requests
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

import auth
import communes
import completion
import departements
import dossier as dossier_mod
import promo
from environment import analyze as env_analyze, listing_facts as env_listing_facts, official as env_official, report as env_report, valuation as env_valuation
import dvf_ingest
import georisques
import hedonic
import iap
import jobs
import legal
import ml_model
import model_store
import notaire
import pack
import photos as photo_ai
import storage
from blend import blend, market_estimate, market_signal
from estimator import METHOD_VERSION, NoDataError, estimate, run_validation
from listing import generate_listing, headline as listing_headline
from models import (ChecklistOverride, DocumentDoc, DocumentValidate, Features, ListingDoc, ListingRequest, PhotoDoc,
                    PropertyDoc, PropertyIn, PropertyUpdate, TargetPriceIn, Weights, utcnow)
from report import build_report
from target import analyze_target

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("estimo")

mongo_url = os.environ["MONGO_URL"]
db_name = os.environ["DB_NAME"]
# Couverture nationale décidée dans le code : une variable d'environnement DVF_DEPARTMENTS figée sur un ancien déploiement
# (ex. 3 départements pilotes) ne doit plus restreindre la zone couverte.
DVF_DEPARTMENTS = departements.ALL_FRANCE
_env_depts = [d.strip() for d in os.environ.get("DVF_DEPARTMENTS", "").split(",") if d.strip()]
if _env_depts and set(_env_depts) != set(DVF_DEPARTMENTS):
    logging.getLogger("server").warning("DVF_DEPARTMENTS (env, %d départements) ignoré : couverture France entière (%d) appliquée", len(_env_depts), len(DVF_DEPARTMENTS))
DVF_YEARS = [int(y) for y in os.environ["DVF_YEARS"].split(",") if y.strip()]
# Les nouveaux millésimes sont intégrés automatiquement : la liste s'étend jusqu'à l'année en cours.
DVF_YEARS = sorted(set(DVF_YEARS) | set(range(max(DVF_YEARS) + 1, datetime.now().year + 1)))
DVF_REFRESH_DAYS = int(os.environ.get("DVF_REFRESH_DAYS", "30"))
BAN_URL = os.environ["BAN_URL"]

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="Achète ma maison API")
api = APIRouter(prefix="/api")          # routes protégées (connexion requise)
public = APIRouter(prefix="/api")       # routes publiques
auth.init(db)
iap.init(db)
promo.init(db)


def _prop_response(doc: dict) -> dict:
    prop = PropertyDoc.from_mongo(doc)
    return {**prop.model_dump(mode="json"), "completion": completion.profile_completion(prop)}


def _oid(pid: str) -> ObjectId:
    try:
        return ObjectId(pid)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Bien introuvable")


async def _run_estimation(p: PropertyIn | PropertyDoc):
    try:
        est = await estimate(
            db, lat=p.lat, lon=p.lon, code_commune=p.code_commune, ptype=p.property_type,
            surface=p.surface, condition=p.condition, year_built=p.year_built, land_surface=p.land_surface,
            features=p.features,
        )
    except NoDataError as exc:
        raise HTTPException(status_code=await _no_data_status(p), detail=await _no_data_message(p, str(exc)))
    # Micro-localisation : ajustements environnement (si l'analyse du bien existe), bornés et transparents
    env_doc = await db.env_analyses.find_one({"_id": p.id}, {"analysis": 1}) if getattr(p, "id", None) else None
    if env_doc and env_doc.get("analysis"):
        env_adj = env_valuation.environment_adjustments(env_doc["analysis"], est.value)
        env_pct = sum(a.pct for a in env_adj)
        if env_adj:
            est.adjustments.extend(env_adj)
            est.value = float(int(round(est.value * (1 + env_pct) / 1000)) * 1000)
            est.low = float(int(round(est.low * (1 + env_pct) / 1000)) * 1000)
            est.high = float(int(round(est.high * (1 + env_pct) / 1000)) * 1000)
            est.price_m2 = float(int(round(est.value / p.surface / 10)) * 10)
            est.notes.append(f"Ajustement environnement {env_pct * 100:+.1f} % appliqué à partir de l'analyse de l'environnement (distances mesurées, sources publiques).")
    features_pct = sum(a.pct for a in est.adjustments if a.key.startswith("feat_"))
    model = await hedonic.load_model(db)
    if model:
        cond = next((a for a in est.adjustments if a.key == "condition"), None)
        year = next((a for a in est.adjustments if a.key == "year"), None)
        try:
            local = await hedonic.local_effect(db, model, lat=p.lat, lon=p.lon, ptype=p.property_type)
            est.hedonic = hedonic.explain(
                model, surface=p.surface, rooms=p.rooms, land=p.land_surface, ptype=p.property_type,
                code_commune=p.code_commune, commune=p.commune, dept=p.code_commune[:2],
                condition_pct=cond.pct if cond else 0.0, condition_label=cond.label if cond else "État correct",
                year_pct=year.pct if year else 0.0, year_label=year.label if year else None,
                comparables_value=est.value, features_pct=features_pct, local=local,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Hedonic explain failed")
    est.market_estimate = market_estimate(est, p.surface)
    ml_meta = await ml_model.load_meta(db)
    if ml_meta:
        cond = next((a for a in est.adjustments if a.key == "condition"), None)
        year = next((a for a in est.adjustments if a.key == "year"), None)
        try:
            est.ml = await asyncio.to_thread(
                ml_model.predict, ml_meta, surface=p.surface, rooms=p.rooms, land=p.land_surface,
                ptype=p.property_type, code_commune=p.code_commune, lat=p.lat, lon=p.lon,
                condition_pct=cond.pct if cond else 0.0, year_pct=(year.pct if year else 0.0) + features_pct)
        except Exception:  # noqa: BLE001
            logger.exception("ML predict failed")
    return est


async def _get_weights() -> Weights:
    doc = await db.settings.find_one({"_id": "weights"}) or {}
    doc.pop("_id", None)
    return Weights(**doc)


# Départements absents de DVF (livre foncier d'Alsace-Moselle, Mayotte) : aucune vente publiée par la DGFiP.
DVF_NOT_COVERED = {"57": "Moselle", "67": "Bas-Rhin", "68": "Haut-Rhin", "976": "Mayotte"}


def _dept_of(code_commune: str | None) -> str:
    c = code_commune or ""
    return c[:3] if c.startswith("97") else c[:2]


async def _dept_loaded(dept: str) -> bool:
    return await db.dvf_sales.count_documents({"dept": dept}, limit=1) > 0


async def _no_data_status(p) -> int:
    dept = _dept_of(getattr(p, "code_commune", None))
    if dept in DVF_NOT_COVERED or await _dept_loaded(dept):
        return 422
    return 503  # données du département pas encore chargées (déploiement récent) : réessayer plus tard


async def _no_data_message(p, default: str) -> str:
    dept = _dept_of(getattr(p, "code_commune", None))
    if dept in DVF_NOT_COVERED:
        return (f"Le département {DVF_NOT_COVERED[dept]} ({dept}) n’est pas couvert par la base DVF de la DGFiP (livre foncier) : "
                "aucune vente de référence n’est publiée, l’estimation par comparables est impossible.")
    if dept and not await _dept_loaded(dept):
        status = await db.dvf_meta.find_one({"_id": "status"}) or {}
        running = status.get("state") == "running" or _ingest_running()
        pct = f" ({round((status.get('progress') or 0) * 100)} %)" if running else ""
        return (f"Les ventes du département {dept} sont en cours de chargement{pct}. Réessayez dans quelques minutes."
                if running else f"Les ventes du département {dept} ne sont pas encore chargées sur ce serveur. Réessayez un peu plus tard ; si le problème persiste, signalez-le.")
    return default


def _ingest_running() -> bool:
    return dvf_ingest.is_running() or jobs.is_running()


async def _ingest_running_anywhere() -> bool:
    """Also true when another process (previous worker after a reload / redeploy) is mid-ingestion, per dvf_meta."""
    if _ingest_running():
        return True
    status = await db.dvf_meta.find_one({"_id": "status"}) or {}
    started = status.get("started_at")
    if status.get("state") != "running" or not started:
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - started).total_seconds() < 12 * 3600


async def _dvf_refresh_loop() -> None:
    """Toutes les 6 h : si le dernier rafraîchissement date de plus de DVF_REFRESH_DAYS jours, relance l'ingestion
    (nouveaux millésimes / fichiers open data mis à jour) puis le réentraînement, en processus enfant basse priorité."""
    await asyncio.sleep(15 * 60)  # laisse le démarrage (et une éventuelle première ingestion) se terminer
    while True:
        try:
            if not _ingest_running() and await db.dvf_sales.estimated_document_count() > 0:
                meta = await db.dvf_meta.find_one({"_id": "refresh"}) or {}
                status = await db.dvf_meta.find_one({"_id": "status"}) or {}
                last = meta.get("last_run") or status.get("finished_at")
                due = last is None or last.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) - timedelta(days=DVF_REFRESH_DAYS)
                if due and jobs.start(jobs.refresh_dvf, mongo_url, db_name, DVF_DEPARTMENTS, DVF_YEARS):
                    logger.info("DVF refresh job started (last run: %s)", last)
        except Exception:  # noqa: BLE001
            logger.exception("DVF refresh scheduler error")
        await asyncio.sleep(6 * 3600)


@public.get("/health")
async def health():
    return {"status": "ok", "app": "Achète ma maison", "departments": DVF_DEPARTMENTS}


@app.get("/health", include_in_schema=False)
async def root_health():
    """Platform health probes hit /health (no /api prefix); must answer fast and never depend on background jobs."""
    return {"status": "ok"}

STORE_ASSETS_DIR = Path(__file__).resolve().parent.parent / "store-assets"


@public.get("/store-assets/{name}", include_in_schema=False)
async def store_asset(name: str):
    """Kit App Store (captures + textes) préparé pour l'éditeur ; fichiers statiques non sensibles."""
    target = (STORE_ASSETS_DIR / name).resolve()
    if not target.is_file() or STORE_ASSETS_DIR not in target.parents or target.suffix not in (".zip", ".md", ".png"):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    media = {".zip": "application/zip", ".md": "text/markdown; charset=utf-8", ".png": "image/png"}[target.suffix]
    return Response(content=target.read_bytes(), media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{target.name}"'})




@public.get("/geocode")
async def geocode(q: str = Query(min_length=3, max_length=200), limit: int = Query(default=6, le=10)):
    def _call():
        return requests.get(BAN_URL, params={"q": q, "limit": limit, "autocomplete": 1}, timeout=8)

    try:
        r = await asyncio.to_thread(_call)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("BAN error: %s", exc)
        raise HTTPException(status_code=502, detail="Service d'adresses indisponible")
    out = []
    for f in r.json().get("features", []):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        dept = p.get("context", "").split(",")[0].strip()
        out.append({
            "id": p.get("id"), "label": p.get("label"), "name": p.get("name"), "postcode": p.get("postcode"),
            "city": p.get("city"), "citycode": p.get("citycode"), "type": p.get("type"),
            "lat": lat, "lon": lon, "dept": dept, "covered": dept in DVF_DEPARTMENTS,
        })
    return {"results": out, "covered_departments": DVF_DEPARTMENTS}


_dvf_stats_cache: dict = {"at": 0.0, "rows": []}


@public.get("/dvf/status")
async def dvf_status():
    meta = await db.dvf_meta.find_one({"_id": "status"}) or {}
    # 4 M+ ventes : l'agrégat par département prend ~4 s → mis en cache 10 min (sauf pendant une ingestion).
    now = time.monotonic()
    if _ingest_running() or now - _dvf_stats_cache["at"] > 600:
        _dvf_stats_cache["rows"] = await db.dvf_sales.aggregate([
            {"$group": {"_id": {"dept": "$dept", "type": "$type"}, "count": {"$sum": 1},
                        "min_date": {"$min": "$date"}, "max_date": {"$max": "$date"}}},
        ]).to_list(None)
        _dvf_stats_cache["at"] = now
    per_dept = _dvf_stats_cache["rows"]
    depts: dict[str, dict] = {}
    for row in per_dept:
        d = depts.setdefault(row["_id"]["dept"], {"dept": row["_id"]["dept"], "appartement": 0, "maison": 0, "total": 0,
                                                 "min_date": None, "max_date": None})
        d[row["_id"]["type"]] = row["count"]
        d["total"] += row["count"]
        for k, fn in (("min_date", min), ("max_date", max)):
            v = row[k].isoformat() if row[k] else None
            d[k] = v if d[k] is None or v is None else fn(d[k], v)
    total = sum(d["total"] for d in depts.values())
    return {
        "state": "running" if _ingest_running() else meta.get("state", "empty" if total == 0 else "idle"),
        "progress": meta.get("progress", 0),
        "error": meta.get("error"),
        "started_at": meta.get("started_at").isoformat() if meta.get("started_at") else None,
        "finished_at": meta.get("finished_at").isoformat() if meta.get("finished_at") else None,
        "configured_departments": DVF_DEPARTMENTS,
        "years": DVF_YEARS,
        "total": total,
        "communes_with_population": await db.communes.estimated_document_count(),
        "departments": sorted(depts.values(), key=lambda d: d["dept"]),
    }


@public.post("/dvf/ingest", status_code=202)
async def dvf_ingest_trigger():
    if _ingest_running():
        return {"started": False, "message": "Ingestion déjà en cours"}
    jobs.start(jobs.ingest_then_train, mongo_url, db_name, DVF_DEPARTMENTS, DVF_YEARS, 0.0)
    return {"started": True, "message": "Ingestion lancée en arrière-plan"}


@public.get("/models/hedonic")
async def hedonic_model():
    model = await hedonic.load_model(db)
    if not model:
        return {"available": False, "training": hedonic.is_training() or jobs.is_running()}
    return {"available": True, "training": hedonic.is_training() or jobs.is_running(), **hedonic.model_summary(model)}


@public.post("/models/hedonic/train", status_code=202)
async def hedonic_train():
    if hedonic.is_training() or jobs.is_running():
        return {"started": False, "message": "Entraînement déjà en cours"}
    jobs.start(jobs.retrain, mongo_url, db_name, "hedonic")
    return {"started": True, "message": "Entraînement lancé en arrière-plan"}


@public.get("/models/ml")
async def ml_meta_route():
    meta = await ml_model.load_meta(db)
    if not meta:
        return {"available": False, "training": ml_model.is_training() or jobs.is_running()}
    meta.pop("_id", None)
    for k in ("trained_at", "data_until"):
        if meta.get(k):
            meta[k] = meta[k].isoformat()
    return {"available": True, "training": ml_model.is_training() or jobs.is_running(), **meta}


@public.post("/models/ml/train", status_code=202)
async def ml_train():
    if ml_model.is_training() or jobs.is_running():
        return {"started": False, "message": "Entraînement déjà en cours"}
    jobs.start(jobs.retrain, mongo_url, db_name, "ml")
    return {"started": True, "message": "Entraînement ML lancé en arrière-plan (≈ 1 min)"}


@public.get("/settings/weights")
async def get_weights():
    return (await _get_weights()).model_dump()


@public.put("/settings/weights")
async def put_weights(w: Weights):
    if w.comparables + w.hedonic + w.market + w.ml <= 0:
        raise HTTPException(status_code=422, detail="Au moins un poids doit être supérieur à 0")
    await db.settings.replace_one({"_id": "weights"}, {"_id": "weights", **w.model_dump()}, upsert=True)
    return w.model_dump()


@api.get("/properties/{pid}/final")
async def property_final(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc or not doc.get("estimation"):
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    return blend(prop.estimation, await _get_weights())


@api.get("/properties/{pid}/market-signal")
async def property_market_signal(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await market_signal(db, lat=doc["lat"], lon=doc["lon"], code_commune=doc["code_commune"],
                               commune=doc["commune"], ptype=doc["property_type"])


# ---------------- Prix cible ----------------

async def _target_payload(doc: dict) -> dict:
    prop = PropertyDoc.from_mongo(doc)
    if prop.target_price is None or not prop.estimation:
        return {"target_price": prop.target_price, "analysis": None}
    final = blend(prop.estimation, await _get_weights())
    try:
        signal = await market_signal(db, lat=prop.lat, lon=prop.lon, code_commune=prop.code_commune,
                                     commune=prop.commune, ptype=prop.property_type)
    except Exception:  # noqa: BLE001
        signal = None
    return {"target_price": prop.target_price,
            "analysis": analyze_target(prop.target_price, prop.surface, prop.estimation, final, signal)}


@api.get("/properties/{pid}/target")
async def get_target(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await _target_payload(doc)


@api.put("/properties/{pid}/target")
async def put_target(pid: str, body: TargetPriceIn):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    await db.properties.update_one({"_id": doc["_id"]}, {"$set": {"target_price": body.target_price, "updated_at": utcnow()}})
    return await _target_payload(await db.properties.find_one({"_id": doc["_id"]}))


# ---------------- Rappels diagnostics ----------------

@api.get("/alerts")
async def alerts(horizon_days: int = Query(default=90, ge=1, le=365)):
    """Expiry reminders: for each (property, checklist item) the most recent validated document with an expiry date."""
    props = {str(p["_id"]): p for p in await db.properties.find({"deleted_at": None, **auth.own()}, {"address_label": 1}).to_list(500)}
    docs = await db.documents.find({"deleted_at": None, "validated": True, "expiry_date": {"$ne": None},
                                    "property_id": {"$in": list(props)}}).to_list(2000)
    latest: dict[tuple[str, str], dict] = {}
    for d in docs:
        k = (d["property_id"], d["item_key"])
        if k not in latest or d["expiry_date"] > latest[k]["expiry_date"]:
            latest[k] = d
    today = datetime.now(timezone.utc).date()
    out = []
    for (pid, item_key), d in latest.items():
        try:
            exp = datetime.strptime(d["expiry_date"][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        days_left = (exp - today).days
        if days_left > horizon_days:
            continue
        level = "expire" if days_left < 0 else "urgent" if days_left <= 30 else "bientot"
        out.append({"property_id": pid, "address_label": props[pid]["address_label"], "document_id": str(d["_id"]),
                    "item_key": item_key, "label": dossier_mod.ITEMS.get(item_key, {}).get("label", item_key),
                    "expiry_date": d["expiry_date"], "days_left": days_left, "level": level})
    out.sort(key=lambda a: a["days_left"])
    return {"as_of": today.isoformat(), "horizon_days": horizon_days, "alerts": out}


# ---------------- Prochaines étapes ----------------

async def _next_steps_for(doc: dict) -> dict:
    pid = str(doc["_id"])
    prop = PropertyDoc.from_mongo(doc)
    steps: list[dict] = []

    def step(key: str, label: str, done: bool, route: str, detail: str = ""):
        steps.append({"key": key, "label": label, "done": done, "route": route, "detail": detail})

    comp = completion.profile_completion(prop)
    step("features", "Compléter les caractéristiques", comp["pct"] >= 70, f"/property/{pid}/edit",
         f"Profil complété à {comp['pct']} % · " + (", ".join(comp["missing"][:3]) + "…" if comp["missing"] else "tout est renseigné"))
    step("target", "Fixer votre prix cible", prop.target_price is not None, f"/property/{pid}/vente",
         "Situez votre prix dans la fourchette et le marché")

    dossier = await _dossier(pid)
    expired = [it for it in dossier["items"] if it["status"] == "expire"]
    to_check = [it for it in dossier["items"] if it["status"] == "a_verifier"]
    missing = [it for it in dossier["items"] if it["required"] and it["status"] == "manquant"]
    dossier_done = not expired and not to_check and not missing
    if expired:
        label, detail = f"Renouveler : {expired[0]['label']}", "Diagnostic expiré, à refaire avant la vente"
    elif to_check:
        label, detail = f"Valider la lecture : {to_check[0]['label']}", "Vérifiez les champs extraits par l'IA"
    elif missing:
        label = f"Ajouter : {missing[0]['label']}"
        detail = f"{len(missing)} document{'s' if len(missing) > 1 else ''} obligatoire{'s' if len(missing) > 1 else ''} manquant{'s' if len(missing) > 1 else ''}"
    else:
        label, detail = "Dossier de vente complet", f"{dossier['progress']['done']}/{dossier['progress']['total_required']} obligatoires validés"
    route = f"/property/{pid}/document/{to_check[0]['documents'][0]['id']}" if to_check and not expired and to_check[0]["documents"] else f"/property/{pid}/dossier"
    step("dossier", label, dossier_done, route, detail)

    n_photos = await db.photos.count_documents({"property_id": pid, "deleted_at": None})
    step("photos", "Ajouter des photos", n_photos > 0, f"/property/{pid}/photos", "Photos retouchées par IA pour l'annonce")
    n_listings = await db.listings.count_documents({"property_id": pid, "deleted_at": None})
    step("listing", "Rédiger l'annonce", n_listings > 0, f"/property/{pid}/listing", "Annonce IA à partir des faits déclarés")
    step("export", "Exporter le dossier pour le notaire", False, f"/property/{pid}/dossier",
         "PDF unique : synthèse + documents validés")

    next_step = next((s for s in steps if not s["done"]), None)
    done = sum(1 for s in steps if s["done"])
    return {"property_id": pid, "steps": steps, "next": next_step, "done": done, "total": len(steps) - 1}


@api.get("/next-steps")
async def next_steps():
    docs = await db.properties.find({"deleted_at": None, **auth.own()}).sort("created_at", -1).to_list(200)
    return {"properties": [await _next_steps_for(d) for d in docs]}


@api.get("/properties/{pid}/next-steps")
async def property_next_steps(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await _next_steps_for(doc)


@api.get("/properties/{pid}/listings")
async def list_listings(pid: str):
    docs = await db.listings.find({"property_id": pid, "deleted_at": None}).sort("created_at", -1).to_list(50)
    out = [ListingDoc.from_mongo(d).model_dump(mode="json") for d in docs]
    if any(not l.get("headline") for l in out):  # annonces antérieures : accroche structurée calculée à la volée
        prop_doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
        if prop_doc:
            line = listing_headline(PropertyDoc.from_mongo(prop_doc))
            for l in out:
                l["headline"] = l.get("headline") or line
    return out


@api.post("/properties/{pid}/listings", status_code=201)
async def create_listing(pid: str, req: ListingRequest):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    await pack.require_unlocked(db, pid, "La rédaction d’annonce par l’IA")
    env_doc = await db.env_analyses.find_one({"_id": pid}, {"analysis": 1}) if req.use_environment else None
    try:
        result = await generate_listing(prop, req.style, req.extra_facts, req.include_price, env=(env_doc or {}).get("analysis"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Listing generation failed")
        raise HTTPException(status_code=502, detail=f"Génération indisponible : {exc}")
    listing = ListingDoc(property_id=pid, style=req.style, extra_facts=req.extra_facts, **result)
    res = await db.listings.insert_one({**listing.to_mongo(), "deleted_at": None, **auth.own()})
    saved = await db.listings.find_one({"_id": res.inserted_id})
    return ListingDoc.from_mongo(saved).model_dump(mode="json")


@api.get("/properties/{pid}/environment/highlights")
async def environment_highlights(pid: str):
    """Atouts du quartier mesurés, depuis le cache uniquement (ne déclenche pas d'analyse)."""
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()}, {"_id": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    env_doc = await db.env_analyses.find_one({"_id": pid}, {"analysis": 1, "created_at": 1})
    if not env_doc:
        return {"available": False, "highlights": []}
    return {"available": True, "created_at": env_doc["created_at"], "highlights": env_listing_facts.neighbourhood_highlights(env_doc["analysis"])}


@api.delete("/properties/{pid}/listings/{lid}")
async def delete_listing(pid: str, lid: str):
    res = await db.listings.update_one({"_id": _oid(lid), "property_id": pid}, {"$set": {"deleted_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    return {"deleted": True}


PHOTO_ORDER = [("position", 1), ("created_at", 1)]


@api.get("/properties/{pid}/photos")
async def list_photos(pid: str):
    docs = await db.photos.find({"property_id": pid, "deleted_at": None}).sort(PHOTO_ORDER).to_list(100)
    return [PhotoDoc.from_mongo(d).model_dump(mode="json") for d in docs]


class PhotoOrder(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)


@api.put("/properties/{pid}/photos/order")
async def reorder_photos(pid: str, body: PhotoOrder):
    """Full order of the bien's photos (first = couverture). Photos omitted from `ids` are appended, in their current order."""
    docs = await db.photos.find({"property_id": pid, "deleted_at": None, **auth.own()}).sort(PHOTO_ORDER).to_list(100)
    if not docs:
        raise HTTPException(status_code=404, detail="Aucune photo pour ce bien")
    known = {str(d["_id"]) for d in docs}
    ordered = [i for i in dict.fromkeys(body.ids) if i in known] + [str(d["_id"]) for d in docs if str(d["_id"]) not in body.ids]
    await asyncio.gather(*(db.photos.update_one({"_id": _oid(photo_id)}, {"$set": {"position": pos}}) for pos, photo_id in enumerate(ordered)))
    return await list_photos(pid)


@api.post("/photos/{photo_id}/cover")
async def set_cover_photo(photo_id: str):
    """Make this photo the couverture (position 0) ; the others keep their relative order."""
    doc = await db.photos.find_one({"_id": _oid(photo_id), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    docs = await db.photos.find({"property_id": doc["property_id"], "deleted_at": None}).sort(PHOTO_ORDER).to_list(100)
    ordered = [photo_id] + [str(d["_id"]) for d in docs if str(d["_id"]) != photo_id]
    await asyncio.gather(*(db.photos.update_one({"_id": _oid(i)}, {"$set": {"position": pos}}) for pos, i in enumerate(ordered)))
    return await list_photos(doc["property_id"])


# Ordre conseillé des photos d'une annonce ; les photos étiquetées sont triées dans cet ordre, les autres suivent.
PHOTO_LABELS = ["Façade", "Salon", "Cuisine", "Jardin", "Suite parentale", "Chambre", "Salle de bains", "Terrasse", "Garage", "Vue extérieure"]


class PhotoLabel(BaseModel):
    label: Optional[Literal["Façade", "Salon", "Cuisine", "Jardin", "Suite parentale", "Chambre", "Salle de bains", "Terrasse", "Garage", "Vue extérieure"]] = None


async def _autosort_photos(pid: str) -> list[dict]:
    """Tri stable : étiquette (ordre conseillé) puis position actuelle ; les photos sans étiquette gardent leur ordre, à la fin."""
    docs = await db.photos.find({"property_id": pid, "deleted_at": None}).sort(PHOTO_ORDER).to_list(100)
    rank = {label: i for i, label in enumerate(PHOTO_LABELS)}
    ordered = sorted(docs, key=lambda d: (rank.get(d.get("label"), len(PHOTO_LABELS)), d.get("position", 0)))
    await asyncio.gather(*(db.photos.update_one({"_id": d["_id"]}, {"$set": {"position": pos}}) for pos, d in enumerate(ordered)))
    return await list_photos(pid)


@api.patch("/photos/{photo_id}")
async def set_photo_label(photo_id: str, body: PhotoLabel):
    """Étiquette la photo (Façade, Salon…) puis retrie automatiquement les photos du bien selon l'ordre conseillé."""
    doc = await db.photos.find_one({"_id": _oid(photo_id), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    await db.photos.update_one({"_id": doc["_id"]}, {"$set": {"label": body.label}})
    return await _autosort_photos(doc["property_id"])


@api.post("/properties/{pid}/photos/autosort")
async def autosort_photos(pid: str):
    """Retrie les photos selon l'ordre conseillé (d'après leurs étiquettes)."""
    if not await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()}):
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await _autosort_photos(pid)


@api.post("/properties/{pid}/photos", status_code=201)
async def upload_photo(pid: str, file: UploadFile = File(...)):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    raw = await file.read()
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo trop lourde (15 Mo max)")
    try:
        data, mime = await asyncio.to_thread(photo_ai.normalize, raw)
    except Exception as exc:  # noqa: BLE001
        # Diagnostic (journal serveur) : type annoncé, nom, taille, signature des premiers octets
        logger.warning("Photo illisible pour %s : content_type=%s filename=%s size=%d magic=%s err=%s", pid, file.content_type, file.filename,
                       len(raw), raw[:12].hex(), str(exc)[:120])
        hint = "fichier vide" if not raw else f"format non reconnu (en-tête {raw[:4].hex()})"
        raise HTTPException(status_code=422, detail=f"Fichier image illisible : {hint}. Formats acceptés : JPEG, PNG, WebP, HEIC.")
    path = f"{storage.APP_NAME}/properties/{pid}/{uuid.uuid4()}.jpg"
    try:
        await asyncio.to_thread(storage.put_object, path, data, mime)
    except storage.StorageError as exc:
        raise HTTPException(status_code=exc.status if exc.status in (402, 503) else 502, detail=str(exc))
    photo = PhotoDoc(property_id=pid, original_path=path, original_mime=mime, original_size=len(data))
    photo.position = await db.photos.count_documents({"property_id": pid, "deleted_at": None})  # appended after existing photos
    res = await db.photos.insert_one({**photo.to_mongo(), "deleted_at": None, "retouched_path": None, **auth.own()})
    saved = await db.photos.find_one({"_id": res.inserted_id})
    return PhotoDoc.from_mongo(saved).model_dump(mode="json")


@api.post("/photos/{photo_id}/retouch")
async def retouch_photo(photo_id: str):
    doc = await db.photos.find_one({"_id": _oid(photo_id), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    if doc.get("status") == "processing":
        raise HTTPException(status_code=409, detail="Retouche déjà en cours")
    await pack.require_unlocked(db, doc["property_id"], "La retouche photo par l’IA")
    await db.photos.update_one({"_id": doc["_id"]}, {"$set": {"status": "processing", "error": None}})
    try:
        original, _ = await asyncio.to_thread(storage.get_object, doc["original_path"])
        edited, mime = await photo_ai.retouch(original)
        path = f"{storage.APP_NAME}/properties/{doc['property_id']}/{uuid.uuid4()}-retouche.jpg"
        await asyncio.to_thread(storage.put_object, path, edited, mime)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Retouch failed")
        await db.photos.update_one({"_id": doc["_id"]}, {"$set": {"status": "error", "error": str(exc)[:300]}})
        raise HTTPException(status_code=502, detail=f"Retouche indisponible : {str(exc)[:200]}")
    await db.photos.update_one({"_id": doc["_id"]}, {"$set": {
        "status": "done", "retouched_path": path, "retouched_mime": mime, "model": photo_ai.MODEL,
        "retouched_at": utcnow(), "error": None}})
    saved = await db.photos.find_one({"_id": doc["_id"]})
    return PhotoDoc.from_mongo(saved).model_dump(mode="json")


@api.get("/photos/{photo_id}/export.jpg")
async def export_photo(photo_id: str, version: Literal["retouched", "original"] = Query(default="retouched")):
    """Signed export (Pack premium): the retouched (or original) photo with the brand watermark, ready to download/share."""
    doc = await db.photos.find_one({"_id": _oid(photo_id), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    await pack.require_unlocked(db, doc["property_id"], "Le téléchargement des photos")
    path = doc.get("retouched_path") if version == "retouched" and doc.get("retouched_path") else doc["original_path"]
    try:
        data, _ = await asyncio.to_thread(storage.get_object, path)
    except storage.StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    out, mime = await asyncio.to_thread(photo_ai.watermark, data)
    filename = f"achetemamaison-{doc['property_id'][-6:]}-{photo_id[-6:]}{'-retouchee' if path != doc['original_path'] else ''}.jpg"
    return Response(content=out, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, max-age=3600"})


@api.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str):
    res = await db.photos.update_one({"_id": _oid(photo_id), "deleted_at": None}, {"$set": {"deleted_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    return {"deleted": True}


# ---------------- Pack annonce premium (Stripe) ----------------

class CheckoutIn(BaseModel):
    return_url: str = Field(min_length=8, max_length=500)


async def _pack_status(pid: str) -> dict:
    await pack.sync_pending(db, pid)
    unlocked = await pack.is_unlocked(db, pid)
    last = await db.orders.find_one({"property_id": pid}, sort=[("created_at", -1)])
    used = await db.photos.count_documents({"property_id": pid, "deleted_at": None, "status": "done"})
    n_photos = await db.photos.count_documents({"property_id": pid, "deleted_at": None})
    n_listings = await db.listings.count_documents({"property_id": pid, "deleted_at": None})
    return {"property_id": pid, "unlocked": unlocked, "price_cents": pack.PACK_PRICE_CENTS, "currency": pack.PACK_CURRENCY,
            "promo_active": promo.user_has_promo(auth.current_user_var.get()),
            **pack.payments_config(), "free_retouches": pack.FREE_RETOUCHES, "retouches_used": used,
            "photos": n_photos, "listings": n_listings,
            "last_order": {"order_id": str(last["_id"]), "status": last["status"], "customer_email": last.get("customer_email"),
                           "receipt_sent": bool(last.get("receipt_sent_at")), "paid_at": last.get("paid_at")} if last else None}


@api.get("/properties/{pid}/pack/status")
async def pack_status(pid: str):
    if not await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await _pack_status(pid)


@api.post("/properties/{pid}/pack/checkout", status_code=201)
async def pack_checkout(pid: str, body: CheckoutIn):
    if not await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Bien introuvable")
    if not body.return_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL de retour invalide")
    if await pack.is_unlocked(db, pid):
        raise HTTPException(status_code=409, detail="Pack déjà débloqué pour ce bien")
    try:
        return await pack.create_checkout(db, pid, body.return_url, auth.owner_id())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stripe checkout failed")
        raise HTTPException(status_code=502, detail=f"Paiement indisponible : {str(exc)[:160]}")


@public.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    try:
        return await pack.handle_webhook(db, await request.body(), request.headers.get("stripe-signature"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)[:160])


@api.get("/properties/{pid}/pack.pdf")
async def pack_pdf(pid: str, style: str = Query(default="sobre"), include_price: bool = Query(default=True)):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    if not await pack.is_unlocked(db, pid):
        raise HTTPException(status_code=402, detail="Pack annonce premium requis (49 €)")
    prop = PropertyDoc.from_mongo(doc)
    listing = await db.listings.find_one({"property_id": pid, "deleted_at": None}, sort=[("created_at", -1)])
    if not listing:
        try:
            result = await generate_listing(prop, style if style in ("sobre", "chaleureux", "premium", "familial") else "sobre", None, include_price)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Génération de l'annonce indisponible : {str(exc)[:160]}")
        listing = ListingDoc(property_id=pid, style=style, extra_facts=None, **result)
        await db.listings.insert_one({**listing.to_mongo(), "deleted_at": None, **auth.own()})
        listing = listing.model_dump()
    listing["headline"] = listing.get("headline") or listing_headline(prop)
    photos = await _property_photos(pid)
    final = blend(prop.estimation, await _get_weights()) if prop.estimation else None
    target = (await _target_payload(doc))["analysis"]
    pdf = await asyncio.to_thread(pack.build_pack_pdf, prop, listing, photos, final, target, include_price)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="estimo-annonce-{pid[-6:]}.pdf"'})


@public.get("/files/{path:path}")
async def get_file(path: str):
    known = await db.photos.find_one({"$or": [{"original_path": path}, {"retouched_path": path}]}, {"_id": 1})
    if not known:
        known = await db.documents.find_one({"file_path": path}, {"_id": 1})
    if not known:
        known = await db.feedback.find_one({"screenshot_path": path}, {"_id": 1})
    if not known:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    try:
        data, mime = await asyncio.to_thread(storage.get_object, path)
    except storage.StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return Response(content=data, media_type=mime, headers={"Cache-Control": "private, max-age=86400"})


# ---------------- Phase 6 — dossier de vente ----------------

def _doc_status(d: dict) -> str:
    if d.get("validated"):
        exp = d.get("expiry_date")
        if exp and exp < datetime.now(timezone.utc).date().isoformat():
            return "expire"
        return "valide"
    if d.get("ocr_status") == "error":
        return "erreur_ocr"
    return "a_verifier"


def _doc_out(d: dict) -> dict:
    out = DocumentDoc.from_mongo(d).model_dump(mode="json")
    out["status"] = _doc_status(d)
    return out


async def _dossier(pid: str) -> dict:
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    # Never wait on georisques.gouv.fr here: use the cached snapshot (even stale) and refresh in the background.
    risks = await georisques.get_cached(db, prop)
    if not georisques.is_fresh(risks):
        await georisques.refresh_in_background(db, prop)
    items = dossier_mod.build_checklist(prop, risks)
    docs, overrides_raw, unlocked = await asyncio.gather(
        db.documents.find({"property_id": pid, "deleted_at": None}).sort("created_at", -1).to_list(300),
        db.checklist_state.find({"property_id": pid}).to_list(100),
        pack.is_unlocked(db, pid),
    )
    overrides = {o["item_key"]: o for o in overrides_raw}
    by_item: dict[str, list[dict]] = {}
    for d in docs:
        by_item.setdefault(d["item_key"], []).append(_doc_out(d))
    done = total_required = 0
    for it in items:
        it["documents"] = by_item.get(it["key"], [])
        ov = overrides.get(it["key"], {})
        it["note"] = ov.get("note")
        if ov.get("status_override") == "non_applicable":
            it["status"] = "non_applicable"
        elif any(d["status"] == "valide" for d in it["documents"]):
            it["status"] = "valide"
        elif any(d["status"] == "expire" for d in it["documents"]):
            it["status"] = "expire"
        elif it["documents"]:
            it["status"] = "a_verifier"
        else:
            it["status"] = "manquant"
        if it["required"] and it["status"] != "non_applicable":
            total_required += 1
            if it["status"] == "valide":
                done += 1
    unassigned = by_item.get("autre", [])
    return {"property_id": pid, "items": items, "unassigned": unassigned,
            "locked": not unlocked,
            "risks": georisques.to_json(risks) if risks else None,
            "progress": {"done": done, "total_required": total_required,
                         "pct": round(done / total_required * 100) if total_required else 100}}


@api.get("/properties/{pid}/risks")
async def property_risks(pid: str, refresh: bool = Query(default=False)):
    """Risques Géorisques (information publique, gratuite) — cache 30 jours par bien."""
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    try:
        risks = await georisques.get_for_property(db, PropertyDoc.from_mongo(doc), force=refresh)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Géorisques indisponible : {str(exc)[:120]}")
    return georisques.to_json(risks)


@api.get("/properties/{pid}/dossier")
async def get_dossier(pid: str):
    return await _dossier(pid)


@api.get("/properties/{pid}/notaire.pdf")
async def notaire_export(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    await pack.require_unlocked(db, pid, "Le dossier de vente et l’export notaire")
    prop = PropertyDoc.from_mongo(doc)
    dossier = await _dossier(pid)
    attachments = notaire.attached_documents(dossier)
    final = blend(prop.estimation, await _get_weights()) if prop.estimation else None
    target = (await _target_payload(doc))["analysis"]

    def _fetch(path: str):
        try:
            return storage.get_object(path)
        except Exception:  # noqa: BLE001
            logger.exception("Attachment fetch failed: %s", path)
            return None

    files = await asyncio.gather(*(asyncio.to_thread(_fetch, a["file_path"]) for a in attachments))
    pdf = await asyncio.to_thread(notaire.build_notaire_pdf, prop, final, dossier, attachments, list(files), target)
    filename = f"estimo-dossier-notaire-{pid[-6:]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@api.put("/properties/{pid}/dossier/{item_key}")
async def override_item(pid: str, item_key: str, body: ChecklistOverride):
    if item_key not in dossier_mod.ITEMS:
        raise HTTPException(status_code=404, detail="Élément de checklist inconnu")
    await pack.require_unlocked(db, pid, "Le dossier de vente")
    await db.checklist_state.replace_one(
        {"property_id": pid, "item_key": item_key},
        {"property_id": pid, "item_key": item_key, "status_override": body.status_override, "note": body.note,
         "updated_at": utcnow()}, upsert=True)
    return await _dossier(pid)


@api.post("/properties/{pid}/documents", status_code=201)
async def upload_document(pid: str, file: UploadFile = File(...), item_key: str = Form(...)):
    if item_key not in dossier_mod.ITEMS and item_key != "autre":
        raise HTTPException(status_code=422, detail="Élément de checklist inconnu")
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    await pack.require_unlocked(db, pid, "Le dossier de vente")
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop lourd (20 Mo max)")
    is_pdf = raw[:5] == b"%PDF-" or (file.content_type == "application/pdf")
    if is_pdf:
        data, mime, ext = raw, "application/pdf", "pdf"
    else:
        try:
            data, mime = await asyncio.to_thread(photo_ai.normalize, raw)
            ext = "jpg"
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="Fichier illisible : PDF ou image attendu")
    path = f"{storage.APP_NAME}/documents/{pid}/{uuid.uuid4()}.{ext}"
    try:
        await asyncio.to_thread(storage.put_object, path, data, mime)
    except storage.StorageError as exc:
        raise HTTPException(status_code=exc.status if exc.status in (402, 503) else 502, detail=str(exc))
    document = DocumentDoc(property_id=pid, item_key=item_key, file_path=path, mime=mime,
                           filename=file.filename or f"document.{ext}", size=len(data))
    res = await db.documents.insert_one({**document.to_mongo(), "deleted_at": None, "ocr": None, "validated_fields": None, **auth.own(),
                                         "expiry_date": None})
    try:
        ocr = await dossier_mod.ocr_document(data, mime, item_key)
        expiry = ocr.get("validity_date") or dossier_mod.expiry_for(item_key, ocr.get("document_date"))
        await db.documents.update_one({"_id": res.inserted_id}, {"$set": {"ocr_status": "done", "ocr": ocr, "expiry_date": expiry}})
    except Exception as exc:  # noqa: BLE001
        logger.exception("OCR failed")
        await db.documents.update_one({"_id": res.inserted_id}, {"$set": {"ocr_status": "error", "ocr_error": str(exc)[:300]}})
    saved = await db.documents.find_one({"_id": res.inserted_id})
    return _doc_out(saved)


@api.get("/documents/{did}")
async def get_document(did: str):
    d = await db.documents.find_one({"_id": _oid(did), "deleted_at": None, **auth.own()})
    if not d:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return _doc_out(d)


@api.post("/documents/{did}/reocr")
async def reocr_document(did: str):
    d = await db.documents.find_one({"_id": _oid(did), "deleted_at": None, **auth.own()})
    if not d:
        raise HTTPException(status_code=404, detail="Document introuvable")
    await pack.require_unlocked(db, d["property_id"], "La lecture automatique des documents par l’IA")
    try:
        data, mime = await asyncio.to_thread(storage.get_object, d["file_path"])
        ocr = await dossier_mod.ocr_document(data, mime, d["item_key"])
        expiry = ocr.get("validity_date") or dossier_mod.expiry_for(d["item_key"], ocr.get("document_date"))
        await db.documents.update_one({"_id": d["_id"]}, {"$set": {"ocr_status": "done", "ocr": ocr, "ocr_error": None, "expiry_date": expiry}})
    except Exception as exc:  # noqa: BLE001
        await db.documents.update_one({"_id": d["_id"]}, {"$set": {"ocr_status": "error", "ocr_error": str(exc)[:300]}})
        raise HTTPException(status_code=502, detail=f"Lecture indisponible : {str(exc)[:200]}")
    return _doc_out(await db.documents.find_one({"_id": d["_id"]}))


@api.put("/documents/{did}/validate")
async def validate_document(did: str, body: DocumentValidate):
    d = await db.documents.find_one({"_id": _oid(did), "deleted_at": None, **auth.own()})
    if not d:
        raise HTTPException(status_code=404, detail="Document introuvable")
    await pack.require_unlocked(db, d["property_id"], "Le dossier de vente")
    fields = body.fields.model_dump()
    item_key = fields["document_type"] if fields["document_type"] in dossier_mod.ITEMS else d["item_key"]
    expiry = fields.get("validity_date") or dossier_mod.expiry_for(item_key, fields.get("document_date"))
    await db.documents.update_one({"_id": d["_id"]}, {"$set": {
        "validated": body.validated, "validated_fields": fields, "item_key": item_key, "expiry_date": expiry,
        "validated_at": utcnow() if body.validated else None}})
    return _doc_out(await db.documents.find_one({"_id": d["_id"]}))


@api.delete("/documents/{did}")
async def delete_document(did: str):
    res = await db.documents.update_one({"_id": _oid(did), "deleted_at": None}, {"$set": {"deleted_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return {"deleted": True}


@api.get("/properties/{pid}/trend")
async def property_trend(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    ptype = doc["property_type"]
    proj = {"year": 1, "price_m2": 1}
    commune_rows = await db.dvf_sales.find({"code_commune": doc["code_commune"], "type": ptype}, proj).to_list(20000)
    near_rows = await db.dvf_sales.find({
        "type": ptype,
        "location": {"$geoWithin": {"$centerSphere": [[doc["lon"], doc["lat"]], 1500 / 6371000.0]}},
    }, proj).to_list(20000)

    def series(rows: list[dict]) -> list[dict]:
        by_year: dict[int, list[float]] = {}
        for r in rows:
            by_year.setdefault(r["year"], []).append(r["price_m2"])
        out = []
        for y in DVF_YEARS:
            vals = sorted(by_year.get(y, []))
            med = vals[len(vals) // 2] if vals else None
            out.append({"year": y, "count": len(vals), "median_pm2": round(med / 10) * 10 if med else None})
        return out

    def change(s: list[dict]) -> Optional[float]:
        pts = [p for p in s if p["median_pm2"] and p["count"] >= 5]
        if len(pts) < 2:
            return None
        return round((pts[-1]["median_pm2"] - pts[0]["median_pm2"]) / pts[0]["median_pm2"], 4)

    cs, ns = series(commune_rows), series(near_rows)
    return {
        "commune": doc["commune"], "property_type": ptype, "years": DVF_YEARS,
        "commune_series": cs, "quartier_series": ns,
        "commune_change_pct": change(cs), "quartier_change_pct": change(ns),
    }


async def _property_photos(pid: str, limit: int = 30) -> list[tuple[bytes, bool]]:
    """(bytes, retouched?) for every photo of the bien, retouched version preferred, in the seller's order (couverture first)."""
    photo_docs = await db.photos.find({"property_id": pid, "deleted_at": None}).sort(PHOTO_ORDER).to_list(limit)

    def _fetch(p: dict):
        path = p.get("retouched_path") if p.get("status") == "done" and p.get("retouched_path") else p["original_path"]
        try:
            return storage.get_object(path)[0], path == p.get("retouched_path")
        except Exception:  # noqa: BLE001
            return None

    return [x for x in await asyncio.gather(*(asyncio.to_thread(_fetch, p) for p in photo_docs)) if x]


@api.get("/properties/{pid}/report.pdf")
async def property_report(pid: str, photos: bool = Query(default=True)):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    if not prop.estimation:
        raise HTTPException(status_code=422, detail="Aucune estimation disponible")
    imgs = await _property_photos(pid, 8) if photos else []
    risks = await db.risks.find_one({"_id": prop.id})
    environment = await db.env_analyses.find_one({"_id": pid}, {"analysis": 1, "report": 1, "created_at": 1})
    pdf = await asyncio.to_thread(build_report, prop, blend(prop.estimation, await _get_weights()), imgs, risks, environment)
    filename = f"estimo-{pid[-6:]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@api.post("/properties", status_code=201)
async def create_property(payload: PropertyIn):
    if payload.property_type == "appartement":
        payload.land_surface = None
    est = await _run_estimation(payload)
    doc = PropertyDoc(**payload.model_dump(), estimation=est)
    res = await db.properties.insert_one({**doc.to_mongo(), **auth.own()})
    await db.estimations.insert_one({"property_id": res.inserted_id, **est.model_dump()})
    saved = await db.properties.find_one({"_id": res.inserted_id})
    return _prop_response(saved)


@api.get("/properties")
async def list_properties():
    docs = await db.properties.find({"deleted_at": None, **auth.own()}).sort("created_at", -1).to_list(200)
    return [_prop_response(d) for d in docs]


@api.get("/properties/{pid}")
async def get_property(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    if (doc.get("estimation") or {}).get("method") != METHOD_VERSION:
        # Estimation engine changed since this bien was estimated: refresh transparently.
        try:
            est = await _run_estimation(PropertyDoc.from_mongo(doc))
        except HTTPException:
            est = None
        if est:
            await db.properties.update_one({"_id": doc["_id"]}, {"$set": {"estimation": est.model_dump(), "updated_at": utcnow()}})
            await db.estimations.insert_one({"property_id": doc["_id"], **est.model_dump()})
            doc = await db.properties.find_one({"_id": doc["_id"]})
    return _prop_response(doc)


@api.put("/properties/{pid}")
async def update_property(pid: str, body: PropertyUpdate):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(prop, k, Features(**v) if k == "features" and v is not None else v)
    if prop.property_type == "appartement":
        prop.land_surface = None
    est = await _run_estimation(prop)
    await db.properties.update_one({"_id": doc["_id"]}, {"$set": {
        **{k: (v if k != "features" else prop.features.model_dump()) for k, v in changes.items()},
        "land_surface": prop.land_surface, "estimation": est.model_dump(), "updated_at": utcnow()}})
    await db.estimations.insert_one({"property_id": doc["_id"], **est.model_dump()})
    return _prop_response(await db.properties.find_one({"_id": doc["_id"]}))


@api.post("/properties/{pid}/reestimate")
async def reestimate_property(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await _reestimate_doc(doc)


async def _reestimate_doc(doc: dict) -> dict:
    prop = PropertyDoc.from_mongo(doc)
    est = await _run_estimation(prop)
    await db.properties.update_one({"_id": doc["_id"]}, {"$set": {"estimation": est.model_dump(), "updated_at": utcnow()}})
    await db.estimations.insert_one({"property_id": doc["_id"], **est.model_dump()})
    saved = await db.properties.find_one({"_id": doc["_id"]})
    return _prop_response(saved)


# ---------------- Analyse de l'environnement ----------------

class AnalyzeIn(BaseModel):
    address: str = Field(min_length=5, max_length=200)
    radii_m: Optional[list[int]] = None
    report: bool = True


async def _risks_for(lat: float, lon: float, code_insee: Optional[str], prop: Optional[PropertyDoc]) -> Optional[dict]:
    """Géorisques : cache du bien si disponible, sinon appel direct borné (jamais bloquant au-delà des timeouts)."""
    try:
        if prop is not None:
            cached = await georisques.get_cached(db, prop)
            if cached:
                return cached
            return await asyncio.wait_for(georisques.get_for_property(db, prop), timeout=25)
        return await asyncio.wait_for(asyncio.to_thread(georisques.fetch, lat, lon, code_insee or ""), timeout=25)
    except Exception:  # noqa: BLE001
        logger.warning("Géorisques indisponible pour l'analyse d'environnement")
        return None


async def _build_environment(*, address: Optional[str], lat: Optional[float], lon: Optional[float], code_insee: Optional[str],
                             radii: Optional[list[int]], prop: Optional[PropertyDoc], with_report: bool,
                             progress: Optional[env_analyze.Progress] = None) -> dict:
    async def step(stage: str, pct: int):
        if progress:
            await progress(stage, pct)

    if lat is None and address:
        await step("Géocodage de l'adresse (BAN)", 3)
        geo, _ = await env_official.geocode(db, address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse introuvable dans la Base Adresse Nationale")
        lat, lon, code_insee = geo["lat"], geo["lon"], geo.get("citycode")
    await step("Risques naturels et technologiques (Géorisques)", 5)
    risks = await _risks_for(lat, lon, code_insee, prop)
    try:
        analysis = await env_analyze.analyze(db, address=address, lon=lon, lat=lat, code_insee=code_insee, radii=radii, risks=risks, on_progress=progress)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    report = None
    if with_report:
        await step("Rédaction de la synthèse par l'IA", 78)
        try:
            report = await env_report.generate_report(analysis)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Environment report failed")
            report = {"error": f"Rapport IA indisponible : {str(exc)[:120]}", "sections": None}
    return {"analysis": analysis, "report": report}


ENV_JOB_STALE_S = 240  # a job without heartbeat for 4 min is considered dead (process restart)


def _env_job_public(job: dict) -> dict:
    return {"status": job["status"], "stage": job.get("stage"), "progress": job.get("progress", 0), "started_at": job.get("started_at"),
            "updated_at": job.get("updated_at"), "error": job.get("error")}


async def _run_environment_job(pid: str, doc: dict) -> None:
    """Analyse d'environnement en arrière-plan ; progression suivie dans `env_jobs` (interrogée par l'app)."""
    async def progress(stage: str, pct: int):
        await db.env_jobs.update_one({"_id": pid}, {"$set": {"stage": stage, "progress": pct, "updated_at": utcnow()}})

    try:
        prop = PropertyDoc.from_mongo(doc)
        out = await _build_environment(address=prop.address_label, lat=prop.lat, lon=prop.lon, code_insee=prop.code_commune, radii=None, prop=prop,
                                       with_report=True, progress=progress)
        now = utcnow()
        await db.env_analyses.replace_one({"_id": pid}, {"_id": pid, "property_id": pid, "created_at": now, **out, "owner_id": doc.get("owner_id")}, upsert=True)
        await progress("Mise à jour de l'estimation", 95)
        try:
            await _reestimate_doc(doc)
        except HTTPException:
            logger.warning("Ré-estimation impossible après analyse d'environnement (%s)", pid)
        await db.env_jobs.update_one({"_id": pid}, {"$set": {"status": "done", "stage": "Analyse terminée", "progress": 100, "updated_at": utcnow()}})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Environment job failed (%s)", pid)
        detail = exc.detail if isinstance(exc, HTTPException) else "Analyse interrompue : une source n'a pas répondu. Réessayez dans un instant."
        await db.env_jobs.update_one({"_id": pid}, {"$set": {"status": "error", "error": str(detail)[:200], "updated_at": utcnow()}})


_env_tasks: set[asyncio.Task] = set()


async def _start_environment_job(pid: str, doc: dict) -> dict:
    job = {"_id": pid, "property_id": pid, "status": "running", "stage": "Préparation de l'analyse", "progress": 1, "error": None,
           "started_at": utcnow(), "updated_at": utcnow()}
    await db.env_jobs.replace_one({"_id": pid}, job, upsert=True)
    task = asyncio.create_task(_run_environment_job(pid, doc))
    _env_tasks.add(task)
    task.add_done_callback(_env_tasks.discard)
    return job


@api.post("/analyze")
async def analyze_address(body: AnalyzeIn):
    """Analyse d'environnement pour une adresse libre (sans bien enregistré)."""
    out = await _build_environment(address=body.address, lat=None, lon=None, code_insee=None, radii=body.radii_m, prop=None, with_report=body.report)
    a = out["analysis"]
    return {"location": {"address": a["address"], "coordinates": a["coordinates"]}, "property": {"parcel": a["parcel"], "building": a["building"]},
            "analysis": {k: v for k, v in a.items() if k not in ("address", "coordinates", "parcel", "building", "sources")},
            "report": out["report"], "sources": a["sources"]}


@api.get("/properties/{pid}/environment")
async def property_environment(pid: str, refresh: bool = Query(default=False)):
    """Analyse d'environnement du bien (cache 30 j), calculée en arrière-plan.

    Répond immédiatement : soit le résultat (`status: done`), soit l'état d'avancement (`status: running`, HTTP 202) à interroger
    toutes les 2 s. Le calcul déclenche une ré-estimation intégrant les ajustements environnement."""
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None, **auth.own()})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    now = datetime.now(timezone.utc)
    job = await db.env_jobs.find_one({"_id": pid})
    if job and job["status"] == "running":
        if job["updated_at"].replace(tzinfo=timezone.utc) > now - timedelta(seconds=ENV_JOB_STALE_S):
            return Response(content=json.dumps({"property_id": pid, **_env_job_public(job)}, default=str), status_code=202, media_type="application/json")
        job = None  # heartbeat perdu (redémarrage) : on relance
    cached = await db.env_analyses.find_one({"_id": pid})
    fresh = cached and cached["created_at"].replace(tzinfo=timezone.utc) > now - timedelta(days=30)
    if fresh and not refresh:
        return {"property_id": pid, "status": "done", "created_at": cached["created_at"], "cached": True, **{k: cached[k] for k in ("analysis", "report")},
                "estimation_adjustments": [a for a in (doc.get("estimation") or {}).get("adjustments", []) if a["key"].startswith("env_")]}
    if job and job["status"] == "error" and not refresh:
        # dernier calcul en échec : pas de relance automatique en boucle, l'app propose « Réessayer » (refresh=true)
        return {"property_id": pid, **_env_job_public(job)}
    job = await _start_environment_job(pid, doc)
    return Response(content=json.dumps({"property_id": pid, **_env_job_public(job)}, default=str), status_code=202, media_type="application/json")


@api.delete("/properties/{pid}")
async def delete_property(pid: str):
    res = await db.properties.update_one({"_id": _oid(pid), "deleted_at": None, **auth.own()},
                                         {"$set": {"deleted_at": utcnow(), "updated_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return {"deleted": True}


@public.post("/estimate/preview")
async def estimate_preview(payload: PropertyIn):
    est = await _run_estimation(payload)
    return est.model_dump(mode="json")


@public.get("/validation")
async def validation(n: int = Query(default=40, ge=5, le=150)):
    report = await run_validation(db, n)
    return report


app.include_router(public)
app.include_router(legal.router, prefix="/api")  # https://<domaine>/api/privacy
app.include_router(legal.router)  # https://<domaine>/privacy (hôte déployé : la racine est servie par l'API)
app.include_router(auth.router)
app.include_router(iap.router, prefix="/api")
app.include_router(promo.router, prefix="/api", dependencies=[Depends(auth.require_user)])
app.include_router(iap.webhook_router, prefix="/api")
app.include_router(api, dependencies=[Depends(auth.require_user)])
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    if os.environ.get("DVF_AUTO_REFRESH", "1") == "1":
        asyncio.create_task(_dvf_refresh_loop())
    await db.properties.create_index([("deleted_at", 1), ("created_at", -1)])
    await db.photos.create_index([("property_id", 1), ("deleted_at", 1)])
    await db.documents.create_index([("property_id", 1), ("deleted_at", 1), ("created_at", -1)])
    await db.checklist_state.create_index([("property_id", 1)])
    await db.orders.create_index([("property_id", 1), ("status", 1)])
    try:
        await asyncio.to_thread(storage.init_storage)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Object storage init failed: %s", exc)
    await iap.ensure_indexes()
    await auth.ensure_indexes()
    count = await db.dvf_sales.estimated_document_count()
    if await db.communes.estimated_document_count() == 0:
        logger.info("Commune populations missing: fetching from geo.api.gouv.fr")
        asyncio.get_running_loop().run_in_executor(None, communes.refresh_populations, mongo_url, db_name, DVF_DEPARTMENTS)
    if count == 0 and not _ingest_running():
        logger.info("DVF collection empty: starting background ingestion for %s", DVF_DEPARTMENTS)
        jobs.start(jobs.ingest_then_train, mongo_url, db_name, DVF_DEPARTMENTS, DVF_YEARS)
    elif count > 0:
        # Cheap path first: seed the shipped model artifacts (no training in the constrained deployment container).
        await asyncio.to_thread(model_store.seed_missing_sync, mongo_url, db_name)
        hed_missing = not await db.models.find_one({"_id": hedonic.MODEL_NAME}) and not hedonic.is_training()
        ml_missing = not await db.models.find_one({"_id": ml_model.MODEL_NAME}) and not ml_model.is_training()
        if hed_missing or ml_missing:
            logger.info("Models missing (hedonic=%s, ml=%s): training in a background process", hed_missing, ml_missing)
            jobs.start(jobs.train_models, mongo_url, db_name, hed_missing, ml_missing)
        # Coverage extended (e.g. 3 départements → France entière): load the départements with no data for a published year.
        pairs = await db.dvf_sales.aggregate([{"$group": {"_id": {"d": "$dept", "y": "$year"}}}]).to_list(None)
        present = {(p["_id"]["d"], p["_id"]["y"]) for p in pairs}
        published_years = {y for _, y in present}  # a year present for at least one département is published
        missing_depts = [d for d in DVF_DEPARTMENTS if any((d, y) not in present for y in published_years)]
        if missing_depts and not await _ingest_running_anywhere():
            logger.info("DVF: %d département(s) à charger : %s", len(missing_depts), ",".join(missing_depts))
            asyncio.get_running_loop().run_in_executor(None, communes.refresh_populations, mongo_url, db_name, missing_depts)
            jobs.start(jobs.ingest_only, mongo_url, db_name, missing_depts, DVF_YEARS)


@app.on_event("shutdown")
async def shutdown():
    client.close()
