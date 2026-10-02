"""Clients des sources officielles. Chaque fonction renvoie (données normalisées | None, source_record)."""
from __future__ import annotations

import json
from typing import Optional

from environment import spatial
from environment.sources import fetch_json

BAN_URL = "https://data.geopf.fr/geocodage/search"
BAN_FALLBACK = "https://api-adresse.data.gouv.fr/search/"
CADASTRE_URL = "https://apicarto.ign.fr/api/cadastre/parcelle"
WFS_URL = "https://data.geopf.fr/wfs/ows"
ALTI_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"
GPU_FEATURE_INFO = "https://www.geoportail-urbanisme.gouv.fr/api/feature-info/du"
GPU_DOCUMENTS = "https://www.geoportail-urbanisme.gouv.fr/api/document"

# BD TOPO v3 : couches et attributs utiles (https://geoservices.ign.fr/documentation/donnees/vecteur/bdtopo)
TOPO_LAYERS = {
    "batiment": ("BDTOPO_V3:batiment", ["nature", "usage_1", "hauteur", "nombre_d_etages", "nombre_de_logements"]),
    "troncon_de_route": ("BDTOPO_V3:troncon_de_route", ["nature", "importance", "nom_collaboratif_gauche", "nombre_de_voies", "vitesse_moyenne_vl"]),
    "troncon_de_voie_ferree": ("BDTOPO_V3:troncon_de_voie_ferree", ["nature", "electrifie", "nombre_de_voies", "vitesse_maximale"]),
    "cours_d_eau": ("BDTOPO_V3:cours_d_eau", ["toponyme", "importance", "caractere_permanent"]),
    "surface_hydrographique": ("BDTOPO_V3:surface_hydrographique", ["nature", "persistance"]),
    "zone_de_vegetation": ("BDTOPO_V3:zone_de_vegetation", ["nature"]),
    "zone_d_activite_ou_d_interet": ("BDTOPO_V3:zone_d_activite_ou_d_interet", ["categorie", "nature", "nature_detaillee", "toponyme", "importance"]),
    "aerodrome": ("BDTOPO_V3:aerodrome", ["nature", "toponyme", "categorie"]),
    "equipement_de_transport": ("BDTOPO_V3:equipement_de_transport", ["nature", "toponyme"]),
    "terrain_de_sport": ("BDTOPO_V3:terrain_de_sport", ["nature"]),
}
# Classes CLC 2018 (niveau 3) les plus courantes
CLC_LABELS = {
    "111": "Tissu urbain continu", "112": "Tissu urbain discontinu", "121": "Zones industrielles ou commerciales", "122": "Réseaux routier et ferroviaire",
    "124": "Aéroports", "131": "Extraction de matériaux", "133": "Chantiers", "141": "Espaces verts urbains", "142": "Équipements sportifs et de loisirs",
    "211": "Terres arables", "221": "Vignobles", "222": "Vergers", "231": "Prairies", "242": "Systèmes culturaux complexes", "243": "Surfaces agricoles avec végétation naturelle",
    "311": "Forêts de feuillus", "312": "Forêts de conifères", "313": "Forêts mélangées", "321": "Pelouses et pâturages naturels", "324": "Forêt et végétation arbustive en mutation",
    "411": "Marais intérieurs", "511": "Cours et voies d'eau", "512": "Plans d'eau",
}


async def geocode(db, address: str) -> tuple[Optional[dict], dict]:
    for url in (BAN_URL, BAN_FALLBACK):
        payload, rec = await fetch_json(db, "ban", url, params={"q": address, "limit": 1}, timeout=10)
        feats = (payload or {}).get("features") or []
        if feats:
            f = feats[0]
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            return {"label": p.get("label"), "lon": lon, "lat": lat, "citycode": p.get("citycode"), "city": p.get("city"),
                    "postcode": p.get("postcode"), "score": p.get("score"), "type": p.get("type"), "housenumber": p.get("housenumber"),
                    "street": p.get("street"), "precision": "numéro" if p.get("type") == "housenumber" else p.get("type")}, rec
    return None, rec


async def parcels(db, lon: float, lat: float, radius_m: float) -> tuple[Optional[list[dict]], dict]:
    """Parcelles cadastrales intersectant l'emprise (point → parcelle du bien ; rayon → voisines)."""
    w, s, e, n = spatial.bbox_around(lon, lat, radius_m)
    geom = json.dumps({"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]})
    payload, rec = await fetch_json(db, "cadastre", CADASTRE_URL, params={"geom": geom, "_limit": 500}, timeout=20)
    if payload is None:
        return None, rec
    out = []
    for f in payload.get("features", []):
        p = f["properties"]
        out.append({"id": f"{p.get('code_insee')}{p.get('section')}{p.get('numero')}", "section": p.get("section"), "numero": p.get("numero"),
                    "code_insee": p.get("code_insee"), "contenance_m2": p.get("contenance"), "geometry": f["geometry"]})
    return out, rec


async def topo_layer(db, layer: str, lon: float, lat: float, radius_m: float, count: int = 500, cql: Optional[str] = None) -> tuple[Optional[list[dict]], dict]:
    typename, attrs = TOPO_LAYERS[layer]
    w, s, e, n = spatial.bbox_around(lon, lat, radius_m)
    params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": typename, "OUTPUTFORMAT": "application/json", "COUNT": count}
    if cql:  # GeoServer n'accepte pas BBOX + CQL_FILTER : l'emprise passe dans le CQL
        params["CQL_FILTER"] = f"({cql}) AND BBOX(geometrie,{w},{s},{e},{n},'EPSG:4326')"
    else:
        params["BBOX"] = f"{s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326"
    payload, rec = await fetch_json(db, "bdtopo", WFS_URL, params=params, timeout=25)
    if payload is None:
        return None, rec
    out = []
    for f in payload.get("features", []):
        p = f.get("properties", {})
        out.append({"id": p.get("cleabs") or f.get("id"), "geometry": f.get("geometry"), **{a: p.get(a) for a in attrs}})
    return out, rec


async def elevation_grid(db, lon: float, lat: float, step_m: float = 25.0) -> tuple[Optional[list[dict]], dict]:
    """9 points (centre + 8 voisins à step_m) pour altitude, pente et orientation."""
    pts = [(lon, lat)]
    for az in (0, 45, 90, 135, 180, 225, 270, 315):
        x, y, _ = spatial.GEOD.fwd(lon, lat, az, step_m)
        pts.append((x, y))
    params = {"lon": "|".join(f"{p[0]:.6f}" for p in pts), "lat": "|".join(f"{p[1]:.6f}" for p in pts), "resource": "ign_rge_alti_wld", "zonly": "false"}
    payload, rec = await fetch_json(db, "alti", ALTI_URL, params=params, timeout=15)
    if payload is None:
        return None, rec
    return payload.get("elevations") or [], rec


async def landcover(db, lon: float, lat: float) -> tuple[Optional[list[dict]], dict]:
    w, s, e, n = spatial.bbox_around(lon, lat, 30)
    params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": "LANDCOVER.CLC18_FR:clc18_fr", "OUTPUTFORMAT": "application/json",
              "BBOX": f"{w},{s},{e},{n},EPSG:4326", "COUNT": 5}
    payload, rec = await fetch_json(db, "clc", WFS_URL, params=params, timeout=20)
    if payload is None:
        return None, rec
    out = []
    for f in payload.get("features", []):
        code = str(f["properties"].get("code_18") or "")
        out.append({"code": code, "label": CLC_LABELS.get(code, f"Classe CLC {code}"), "area_ha": f["properties"].get("area_ha"), "geometry": f.get("geometry")})
    return out, rec


async def gpu_point(db, lon: float, lat: float) -> tuple[Optional[dict], dict]:
    """Zonage, prescriptions, informations et servitudes au point (API GPU officielle)."""
    payload, rec = await fetch_json(db, "gpu", GPU_FEATURE_INFO, params={"lon": f"{lon:.6f}", "lat": f"{lat:.6f}"}, timeout=40, retries=1)
    if payload is None:
        return None, rec
    zones, prescriptions, infos, sups, docs = [], [], [], [], []
    for f in payload.get("features", []):
        kind = str(f.get("id", "")).split(".")[0]
        p = f.get("properties", {})
        item = {"libelle": p.get("libelle"), "libelong": p.get("libelong"), "typezone": p.get("typezone"), "reglement": p.get("nomfic"),
                "url": p.get("urlfic") or None, "date_approbation": p.get("datappro"), "geometry": f.get("geometry") if kind == "zone_urba" else None}
        if kind == "zone_urba":
            zones.append(item)
        elif kind.startswith("prescription") or kind == "secteur_cc":
            prescriptions.append({**item, "type": kind})
        elif kind.startswith("info"):
            infos.append({**item, "type": kind})
        elif "sup" in kind:
            sups.append({**item, "type": kind})
        elif kind == "document":
            docs.append({"id": f.get("id"), "type": p.get("typedoc"), "etat": p.get("etat"), "date_approbation": p.get("datappro"), "partition": p.get("partition")})
    return {"zones": zones, "prescriptions": prescriptions, "infos": infos, "servitudes": sups, "documents": docs}, rec


async def gpu_documents(db, code_insee: str) -> tuple[Optional[list[dict]], dict]:
    payload, rec = await fetch_json(db, "gpu", GPU_DOCUMENTS, params={"grid_name": code_insee, "status": "document.production"}, timeout=20)
    if payload is None:
        return None, rec
    return [{"id": d.get("id"), "type": d.get("documentType") or d.get("type"), "name": d.get("name"), "legal_status": d.get("legalStatus"),
             "approval_date": d.get("approvalDate"), "publication_date": d.get("publicationDate"),
             "url": f"https://www.geoportail-urbanisme.gouv.fr/document/by-id/{d.get('id')}"} for d in payload if isinstance(d, dict)], rec
