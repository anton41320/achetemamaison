from __future__ import annotations

import asyncio
import logging
import os
from datetime import timezone
from pathlib import Path
from typing import Optional

import requests
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

import dvf_ingest
import hedonic
import ml_model
from blend import blend, market_estimate, market_signal
from estimator import NoDataError, estimate, run_validation
from listing import generate_listing
from models import ListingDoc, ListingRequest, PropertyDoc, PropertyIn, Weights, utcnow
from report import build_report

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("estimo")

mongo_url = os.environ["MONGO_URL"]
db_name = os.environ["DB_NAME"]
DVF_DEPARTMENTS = [d.strip() for d in os.environ["DVF_DEPARTMENTS"].split(",") if d.strip()]
DVF_YEARS = [int(y) for y in os.environ["DVF_YEARS"].split(",") if y.strip()]
BAN_URL = os.environ["BAN_URL"]

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="Estimo API")
api = APIRouter(prefix="/api")


def _prop_response(doc: dict) -> dict:
    return PropertyDoc.from_mongo(doc).model_dump(mode="json")


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
        )
    except NoDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    model = await hedonic.load_model(db)
    if model:
        cond = next((a for a in est.adjustments if a.key == "condition"), None)
        year = next((a for a in est.adjustments if a.key == "year"), None)
        try:
            est.hedonic = hedonic.explain(
                model, surface=p.surface, rooms=p.rooms, land=p.land_surface, ptype=p.property_type,
                code_commune=p.code_commune, commune=p.commune, dept=p.code_commune[:2],
                condition_pct=cond.pct if cond else 0.0, condition_label=cond.label if cond else "État correct",
                year_pct=year.pct if year else 0.0, year_label=year.label if year else None,
                comparables_value=est.value,
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
                condition_pct=cond.pct if cond else 0.0, year_pct=year.pct if year else 0.0)
        except Exception:  # noqa: BLE001
            logger.exception("ML predict failed")
    return est


async def _get_weights() -> Weights:
    doc = await db.settings.find_one({"_id": "weights"}) or {}
    doc.pop("_id", None)
    return Weights(**doc)


def _ingest_then_train():
    dvf_ingest.ingest_all(mongo_url, db_name, DVF_DEPARTMENTS, DVF_YEARS)
    hedonic.train(mongo_url, db_name)
    ml_model.train(mongo_url, db_name)


@api.get("/health")
async def health():
    return {"status": "ok", "app": "Estimo", "departments": DVF_DEPARTMENTS}


@api.get("/geocode")
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


@api.get("/dvf/status")
async def dvf_status():
    meta = await db.dvf_meta.find_one({"_id": "status"}) or {}
    per_dept = await db.dvf_sales.aggregate([
        {"$group": {"_id": {"dept": "$dept", "type": "$type"}, "count": {"$sum": 1},
                    "min_date": {"$min": "$date"}, "max_date": {"$max": "$date"}}},
    ]).to_list(50)
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
        "state": "running" if dvf_ingest.is_running() else meta.get("state", "empty" if total == 0 else "idle"),
        "progress": meta.get("progress", 0),
        "error": meta.get("error"),
        "started_at": meta.get("started_at").isoformat() if meta.get("started_at") else None,
        "finished_at": meta.get("finished_at").isoformat() if meta.get("finished_at") else None,
        "configured_departments": DVF_DEPARTMENTS,
        "years": DVF_YEARS,
        "total": total,
        "departments": sorted(depts.values(), key=lambda d: d["dept"]),
    }


@api.post("/dvf/ingest", status_code=202)
async def dvf_ingest_trigger():
    if dvf_ingest.is_running():
        return {"started": False, "message": "Ingestion déjà en cours"}
    asyncio.get_running_loop().run_in_executor(None, _ingest_then_train)
    return {"started": True, "message": "Ingestion lancée en arrière-plan"}


@api.get("/models/hedonic")
async def hedonic_model():
    model = await hedonic.load_model(db)
    if not model:
        return {"available": False, "training": hedonic.is_training()}
    return {"available": True, "training": hedonic.is_training(), **hedonic.model_summary(model)}


@api.post("/models/hedonic/train", status_code=202)
async def hedonic_train():
    if hedonic.is_training():
        return {"started": False, "message": "Entraînement déjà en cours"}
    asyncio.get_running_loop().run_in_executor(None, hedonic.train, mongo_url, db_name)
    return {"started": True, "message": "Entraînement lancé en arrière-plan"}


@api.get("/models/ml")
async def ml_meta_route():
    meta = await ml_model.load_meta(db)
    if not meta:
        return {"available": False, "training": ml_model.is_training()}
    meta.pop("_id", None)
    for k in ("trained_at", "data_until"):
        if meta.get(k):
            meta[k] = meta[k].isoformat()
    return {"available": True, "training": ml_model.is_training(), **meta}


@api.post("/models/ml/train", status_code=202)
async def ml_train():
    if ml_model.is_training():
        return {"started": False, "message": "Entraînement déjà en cours"}
    asyncio.get_running_loop().run_in_executor(None, ml_model.train, mongo_url, db_name)
    return {"started": True, "message": "Entraînement ML lancé en arrière-plan (≈ 1 min)"}


@api.get("/settings/weights")
async def get_weights():
    return (await _get_weights()).model_dump()


@api.put("/settings/weights")
async def put_weights(w: Weights):
    if w.comparables + w.hedonic + w.market + w.ml <= 0:
        raise HTTPException(status_code=422, detail="Au moins un poids doit être supérieur à 0")
    await db.settings.replace_one({"_id": "weights"}, {"_id": "weights", **w.model_dump()}, upsert=True)
    return w.model_dump()


@api.get("/properties/{pid}/final")
async def property_final(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
    if not doc or not doc.get("estimation"):
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    return blend(prop.estimation, await _get_weights())


@api.get("/properties/{pid}/market-signal")
async def property_market_signal(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return await market_signal(db, lat=doc["lat"], lon=doc["lon"], code_commune=doc["code_commune"],
                               commune=doc["commune"], ptype=doc["property_type"])


@api.get("/properties/{pid}/listings")
async def list_listings(pid: str):
    docs = await db.listings.find({"property_id": pid, "deleted_at": None}).sort("created_at", -1).to_list(50)
    return [ListingDoc.from_mongo(d).model_dump(mode="json") for d in docs]


@api.post("/properties/{pid}/listings", status_code=201)
async def create_listing(pid: str, req: ListingRequest):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    try:
        result = await generate_listing(prop, req.style, req.extra_facts, req.include_price)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Listing generation failed")
        raise HTTPException(status_code=502, detail=f"Génération indisponible : {exc}")
    listing = ListingDoc(property_id=pid, style=req.style, extra_facts=req.extra_facts, **result)
    res = await db.listings.insert_one({**listing.to_mongo(), "deleted_at": None})
    saved = await db.listings.find_one({"_id": res.inserted_id})
    return ListingDoc.from_mongo(saved).model_dump(mode="json")


@api.delete("/properties/{pid}/listings/{lid}")
async def delete_listing(pid: str, lid: str):
    res = await db.listings.update_one({"_id": _oid(lid), "property_id": pid}, {"$set": {"deleted_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    return {"deleted": True}


@api.get("/properties/{pid}/trend")
async def property_trend(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
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


@api.get("/properties/{pid}/report.pdf")
async def property_report(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    if not prop.estimation:
        raise HTTPException(status_code=422, detail="Aucune estimation disponible")
    pdf = await asyncio.to_thread(build_report, prop, blend(prop.estimation, await _get_weights()))
    filename = f"estimo-{pid[-6:]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@api.post("/properties", status_code=201)
async def create_property(payload: PropertyIn):
    if payload.property_type == "appartement":
        payload.land_surface = None
    est = await _run_estimation(payload)
    doc = PropertyDoc(**payload.model_dump(), estimation=est)
    res = await db.properties.insert_one(doc.to_mongo())
    await db.estimations.insert_one({"property_id": res.inserted_id, **est.model_dump()})
    saved = await db.properties.find_one({"_id": res.inserted_id})
    return _prop_response(saved)


@api.get("/properties")
async def list_properties():
    docs = await db.properties.find({"deleted_at": None}).sort("created_at", -1).to_list(200)
    return [_prop_response(d) for d in docs]


@api.get("/properties/{pid}")
async def get_property(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return _prop_response(doc)


@api.post("/properties/{pid}/reestimate")
async def reestimate_property(pid: str):
    doc = await db.properties.find_one({"_id": _oid(pid), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    prop = PropertyDoc.from_mongo(doc)
    est = await _run_estimation(prop)
    await db.properties.update_one({"_id": doc["_id"]}, {"$set": {"estimation": est.model_dump(), "updated_at": utcnow()}})
    await db.estimations.insert_one({"property_id": doc["_id"], **est.model_dump()})
    saved = await db.properties.find_one({"_id": doc["_id"]})
    return _prop_response(saved)


@api.delete("/properties/{pid}")
async def delete_property(pid: str):
    res = await db.properties.update_one({"_id": _oid(pid), "deleted_at": None},
                                         {"$set": {"deleted_at": utcnow(), "updated_at": utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bien introuvable")
    return {"deleted": True}


@api.post("/estimate/preview")
async def estimate_preview(payload: PropertyIn):
    est = await _run_estimation(payload)
    return est.model_dump(mode="json")


@api.get("/validation")
async def validation(n: int = Query(default=40, ge=5, le=150)):
    report = await run_validation(db, n)
    return report


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await db.properties.create_index([("deleted_at", 1), ("created_at", -1)])
    count = await db.dvf_sales.estimated_document_count()
    if count == 0 and not dvf_ingest.is_running():
        logger.info("DVF collection empty: starting background ingestion for %s", DVF_DEPARTMENTS)
        asyncio.get_running_loop().run_in_executor(None, _ingest_then_train)
    elif not await db.models.find_one({"_id": hedonic.MODEL_NAME}) and not hedonic.is_training():
        logger.info("Hedonic model missing: training in background")
        asyncio.get_running_loop().run_in_executor(None, hedonic.train, mongo_url, db_name)
    if count > 0 and not await db.models.find_one({"_id": ml_model.MODEL_NAME}) and not ml_model.is_training():
        logger.info("ML model missing: training in background")
        asyncio.get_running_loop().run_in_executor(None, ml_model.train, mongo_url, db_name)


@app.on_event("shutdown")
async def shutdown():
    client.close()
