"""Offline DVF ingestion pipeline.

Downloads the geolocated DVF CSV files published on data.gouv.fr
(files.data.gouv.fr/geo-dvf) for a list of departments and years, keeps only
clean single-dwelling sales (one Maison or one Appartement per mutation, a single
price) and stores them in MongoDB with a 2dsphere index for radius queries.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from pymongo import ASCENDING, GEOSPHERE, MongoClient

logger = logging.getLogger("dvf_ingest")

DATA_DIR = Path(__file__).parent / "data" / "dvf"
BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dept}.csv.gz"

USECOLS = [
    "id_mutation", "date_mutation", "nature_mutation", "valeur_fonciere",
    "code_postal", "code_commune", "nom_commune", "code_departement", "id_parcelle",
    "type_local", "surface_reelle_bati", "nombre_pieces_principales", "surface_terrain",
    "longitude", "latitude",
]

_lock = threading.Lock()
_running = False


def is_running() -> bool:
    return _running


class NotPublished(Exception):
    """Le millésime n'est pas (encore) publié en open data (fichier 404)."""


def download(dept: str, year: int, force: bool = False, known_size: int | None = None) -> tuple[Path | None, bool]:
    """Télécharge le fichier s'il manque (ou si `force` et que la version distante a changé). Retourne (chemin, modifié)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{dept}_{year}.csv.gz"
    exists = path.exists() and path.stat().st_size > 1000
    if exists and not force:
        return path, False
    url = BASE_URL.format(year=year, dept=dept)
    local_size = path.stat().st_size if exists else known_size  # les .gz sont supprimés après ingestion : la taille est mémorisée en base
    if force and local_size:  # rafraîchissement : ne re-télécharger que si la taille distante diffère
        try:
            head = requests.head(url, timeout=60, allow_redirects=True)
            if head.status_code == 404:
                raise NotPublished(url)
            remote = int(head.headers.get("Content-Length") or -1)
            if remote == local_size:
                return (path if exists else None), False
        except requests.RequestException:
            return (path if exists else None), False
    logger.info("Downloading %s", url)
    with requests.get(url, timeout=180, stream=True) as r:
        if r.status_code == 404:
            raise NotPublished(url)
        r.raise_for_status()
        tmp = path.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        if exists and tmp.stat().st_size == path.stat().st_size:
            tmp.unlink()
            return path, False
        tmp.replace(path)
    return path, True


def parse_file(path: Path, dept: str, year: int) -> list[dict]:
    df = pd.read_csv(
        path, compression="gzip", usecols=USECOLS, low_memory=False,
        dtype={"code_postal": str, "code_commune": str, "code_departement": str, "id_parcelle": str},
    )
    df = df[df["nature_mutation"] == "Vente"]
    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
    df = df.dropna(subset=["valeur_fonciere"])

    # A mutation must carry a single price to be interpretable.
    price_n = df.groupby("id_mutation")["valeur_fonciere"].nunique()
    df = df[df["id_mutation"].isin(price_n[price_n == 1].index)]

    # Dwellings: exactly one Maison or Appartement per mutation.
    loc = df[df["type_local"].isin(["Maison", "Appartement"])].copy()
    loc = loc.drop_duplicates(subset=["id_mutation", "type_local", "surface_reelle_bati", "nombre_pieces_principales"])
    cnt = loc.groupby("id_mutation").size()
    loc = loc[loc["id_mutation"].isin(cnt[cnt == 1].index)]
    loc = loc.dropna(subset=["longitude", "latitude", "surface_reelle_bati"])

    # Land: sum of parcel surfaces of the mutation (one row per parcel).
    land = df.drop_duplicates(subset=["id_mutation", "id_parcelle"]).groupby("id_mutation")["surface_terrain"].sum(min_count=1)
    loc = loc.join(land.rename("land_total"), on="id_mutation")

    loc["price_m2"] = loc["valeur_fonciere"] / loc["surface_reelle_bati"]
    loc = loc[
        (loc["surface_reelle_bati"] >= 9)
        & (loc["surface_reelle_bati"] <= 600)
        & (loc["valeur_fonciere"] >= 5000)
        & (loc["price_m2"].between(200, 12000))
    ]

    docs: list[dict] = []
    for row in loc.itertuples(index=False):
        ptype = "maison" if row.type_local == "Maison" else "appartement"
        land_total = row.land_total if ptype == "maison" and pd.notna(row.land_total) else 0.0
        date = datetime.strptime(str(row.date_mutation), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        docs.append({
            "mutation_id": row.id_mutation,
            "date": date,
            "year": year,
            "dept": dept,
            "type": ptype,
            "price": float(row.valeur_fonciere),
            "surface": float(row.surface_reelle_bati),
            "rooms": int(row.nombre_pieces_principales) if pd.notna(row.nombre_pieces_principales) else None,
            "land_surface": float(min(land_total, 50000)),
            "price_m2": round(float(row.price_m2), 2),
            "code_commune": str(row.code_commune),
            "commune": str(row.nom_commune),
            "code_postal": str(row.code_postal) if pd.notna(row.code_postal) else "",
            "location": {"type": "Point", "coordinates": [float(row.longitude), float(row.latitude)]},
        })
    return docs


def ensure_indexes(db) -> None:
    db.dvf_sales.create_index([("location", GEOSPHERE)])
    db.dvf_sales.create_index([("code_commune", ASCENDING), ("type", ASCENDING), ("date", ASCENDING)])
    db.dvf_sales.create_index([("dept", ASCENDING), ("year", ASCENDING)])
    db.dvf_sales.create_index([("mutation_id", ASCENDING)])


def ingest_all(mongo_url: str, db_name: str, depts: list[str], years: list[int], force: bool = False) -> int:
    """Ingestion (ou rafraîchissement si `force`). Retourne le nombre de fichiers (dept, année) réellement mis à jour."""
    global _running
    changed_files = 0
    with _lock:
        if _running:
            return 0
        _running = True
    client = MongoClient(mongo_url)
    db = client[db_name]
    meta = db.dvf_meta
    total_steps = len(depts) * len(years)
    done = 0
    try:
        ensure_indexes(db)
        meta.update_one(
            {"_id": "status"},
            {"$set": {"state": "running", "progress": 0, "error": None, "started_at": datetime.now(timezone.utc),
                      "departments": depts, "years": years}},
            upsert=True,
        )
        for dept in depts:
            for year in years:
                try:
                    known = db.dvf_files.find_one({"_id": f"{dept}_{year}"}, {"size": 1})
                    path, changed = download(dept, year, force=force, known_size=(known or {}).get("size"))
                    already = path is None or (force and not changed and db.dvf_sales.count_documents({"dept": dept, "year": year}, limit=1) > 0)
                    if already:
                        logger.info("Unchanged %s/%s", dept, year)
                    else:
                        size = path.stat().st_size
                        docs = parse_file(path, dept, year)
                        db.dvf_sales.delete_many({"dept": dept, "year": year})
                        for i in range(0, len(docs), 5000):
                            db.dvf_sales.insert_many(docs[i:i + 5000])
                        db.dvf_files.replace_one({"_id": f"{dept}_{year}"}, {"_id": f"{dept}_{year}", "dept": dept, "year": year, "size": size,
                                                                            "sales": len(docs), "ingested_at": datetime.now(timezone.utc)}, upsert=True)
                        path.unlink(missing_ok=True)  # France entière ≈ plusieurs Go de .gz : on ne garde pas les fichiers
                        changed_files += 1
                        logger.info("Ingested %s/%s: %d sales", dept, year, len(docs))
                except NotPublished:
                    logger.info("Not published yet: %s/%s", dept, year)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed %s/%s", dept, year)
                    meta.update_one({"_id": "status"}, {"$set": {"error": f"{dept}/{year}: {exc}"}})
                done += 1
                meta.update_one({"_id": "status"}, {"$set": {"progress": round(done / total_steps, 3)}})
        meta.update_one(
            {"_id": "status"},
            {"$set": {"state": "idle", "progress": 1.0, "finished_at": datetime.now(timezone.utc)}},
        )
    finally:
        _running = False
        client.close()
    return changed_files
