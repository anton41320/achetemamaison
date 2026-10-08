"""Orchestration : collecte parallèle des sources, calculs spatiaux, JSON consolidé et sourcé."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from shapely.geometry import Point, mapping

from environment import official, osm, spatial

logger = logging.getLogger("environment")

DEFAULT_RADII = [50, 250, 1000, 5000]
ROAD_IMPORTANCE = {"1": "axe autoroutier ou majeur", "2": "axe principal (liaison entre agglomérations)", "3": "axe secondaire structurant",
                   "4": "voie de desserte", "5": "voie locale", "6": "chemin, sentier ou escalier"}  # importance fonctionnelle BD TOPO
ZAI_SERVICE = {"Science et enseignement": "ecole", "Santé": "sante", "Sport": "sport", "Culture et loisirs": "culture",
               "Administratif ou militaire": "service_public", "Transport": "transport", "Religieux": "culture", "Gestion des eaux": "technique"}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _feat(item: dict, origin: Point, radii: list[int], lon: float, lat: float) -> Optional[dict]:
    g = spatial.geojson_to_metric(item.get("geometry") or {})
    if g is None:
        return None
    d = spatial.distance_m(origin, g)
    c = spatial.to_wgs(g.representative_point())
    out = {k: v for k, v in item.items() if k != "geometry"}
    out.update({"distance_m": round(d), "ring": spatial.ring_label(d, radii), "direction": spatial.bearing_label(lon, lat, c.x, c.y) if d > 5 else "sur place",
                "lon": round(c.x, 6), "lat": round(c.y, 6)})
    return out, g  # type: ignore[return-value]


Progress = Callable[[str, int], Awaitable[None]]


async def analyze(db, *, address: Optional[str] = None, lon: Optional[float] = None, lat: Optional[float] = None,
                  code_insee: Optional[str] = None, radii: Optional[list[int]] = None, risks: Optional[dict] = None,
                  on_progress: Optional[Progress] = None) -> dict:
    radii = sorted(radii or DEFAULT_RADII)
    rmax = radii[-1]
    sources: list[dict] = []
    unavailable: list[str] = []

    async def progress(stage: str, pct: int):
        if on_progress:
            try:
                await on_progress(stage, pct)
            except Exception:  # noqa: BLE001
                logger.debug("progress callback failed", exc_info=True)

    def keep(rec: dict, what: str):
        sources.append({**rec, "what": what})
        if rec.get("status") != "ok":
            unavailable.append(what)

    geo = None
    if lon is None or lat is None:
        if not address:
            raise ValueError("Adresse ou coordonnées requises")
        await progress("Géocodage de l'adresse (BAN)", 8)
        geo, rec = await official.geocode(db, address)
        keep(rec, "Géocodage de l'adresse")
        if not geo:
            raise LookupError("Adresse introuvable dans la Base Adresse Nationale")
        lon, lat, code_insee = geo["lon"], geo["lat"], geo.get("citycode") or code_insee
    origin = spatial.point_metric(lon, lat)

    r_local, r_mid = min(250, radii[min(1, len(radii) - 1)]), min(1000, radii[min(2, len(radii) - 1)])
    tasks = {
        "parcels": official.parcels(db, lon, lat, 120),
        "buildings": official.topo_layer(db, "batiment", lon, lat, r_local, count=800),
        "roads": official.topo_layer(db, "troncon_de_route", lon, lat, r_mid, count=800),
        "roads_major": official.topo_layer(db, "troncon_de_route", lon, lat, rmax, count=400, cql="importance IN ('1','2')"),
        "rail": official.topo_layer(db, "troncon_de_voie_ferree", lon, lat, min(2000, rmax), count=200),
        "rivers": official.topo_layer(db, "cours_d_eau", lon, lat, r_mid, count=100),
        "water": official.topo_layer(db, "surface_hydrographique", lon, lat, r_mid, count=200),
        "vegetation": official.topo_layer(db, "zone_de_vegetation", lon, lat, r_mid, count=600),
        "zai": official.topo_layer(db, "zone_d_activite_ou_d_interet", lon, lat, min(2000, rmax), count=600),
        "aerodrome": official.topo_layer(db, "aerodrome", lon, lat, rmax, count=20),
        "transport": official.topo_layer(db, "equipement_de_transport", lon, lat, r_mid, count=200),
        "sport": official.topo_layer(db, "terrain_de_sport", lon, lat, r_mid, count=200),
        "alti": official.elevation_grid(db, lon, lat),
        "clc": official.landcover(db, lon, lat),
        "gpu": official.gpu_point(db, lon, lat),
        "gpu_docs": official.gpu_documents(db, code_insee) if code_insee else asyncio.sleep(0, result=(None, None)),
        "osm": osm.pois(db, lon, lat, min(1500, rmax)),
    }
    labels = {"parcels": "Parcelles cadastrales", "buildings": "Bâtiments (BD TOPO)", "roads": "Routes (BD TOPO)", "roads_major": "Grands axes (BD TOPO)",
              "rail": "Voies ferrées (BD TOPO)", "rivers": "Cours d'eau (BD TOPO)", "water": "Surfaces en eau (BD TOPO)", "vegetation": "Végétation (BD TOPO)",
              "zai": "Zones d'activité et d'intérêt (BD TOPO)", "aerodrome": "Aérodromes (BD TOPO)", "transport": "Équipements de transport (BD TOPO)",
              "sport": "Terrains de sport (BD TOPO)", "alti": "Altimétrie (RGE ALTI)", "clc": "Occupation du sol (CLC 2018)", "gpu": "Urbanisme au point (GPU)",
              "gpu_docs": "Documents d'urbanisme (GPU)", "osm": "Services et commerces (OpenStreetMap)"}
    done_count = 0

    async def tracked(key: str, coro):
        nonlocal done_count
        try:
            return await coro
        finally:
            done_count += 1
            await progress(f"{labels[key]} · {done_count}/{len(tasks)} sources", 10 + round(55 * done_count / len(tasks)))

    await progress("Interrogation des sources officielles (IGN, Cadastre, GPU, OSM)", 10)
    results = dict(zip(tasks.keys(), await asyncio.gather(*(tracked(k, c) for k, c in tasks.items()), return_exceptions=True)))
    data: dict[str, Any] = {}
    await progress("Calculs spatiaux (distances, densité, pente)", 68)
    for k, res in results.items():
        if isinstance(res, BaseException):
            logger.warning("%s failed: %s", k, res)
            data[k] = None
            unavailable.append(labels[k])
            continue
        payload, rec = res
        data[k] = payload
        if rec:
            keep(rec, labels[k])

    # ---- parcelle et bâtiment du bien
    parcel, parcel_geom, nearby_parcels = None, None, []
    for p in data.get("parcels") or []:
        g = spatial.geojson_to_metric(p["geometry"])
        if g is None:
            continue
        if parcel is None and g.contains(origin):
            parcel, parcel_geom = p, g
    if parcel is None and data.get("parcels"):
        cands = [(spatial.distance_m(origin, spatial.geojson_to_metric(p["geometry"])), p) for p in data["parcels"] if spatial.geojson_to_metric(p["geometry"]) is not None]
        if cands:
            d, p = min(cands, key=lambda x: x[0])
            if d < 15:
                parcel, parcel_geom = p, spatial.geojson_to_metric(p["geometry"])
    bgeoms = []
    for b in data.get("buildings") or []:
        g = spatial.geojson_to_metric(b["geometry"])
        if g is not None:
            bgeoms.append((b, g))
    building = None
    if parcel_geom is not None:
        on_parcel = [(b, g) for b, g in bgeoms if g.intersects(parcel_geom)]
        if on_parcel:
            b, g = max(on_parcel, key=lambda x: x[1].intersection(parcel_geom).area)
            building = {**{k: v for k, v in b.items() if k != "geometry"}, "footprint_m2": round(g.area), "geometry": mapping(spatial.to_wgs(g))}
    if building is None and bgeoms:
        b, g = min(bgeoms, key=lambda x: spatial.distance_m(origin, x[1]))
        if spatial.distance_m(origin, g) < 25:
            building = {**{k: v for k, v in b.items() if k != "geometry"}, "footprint_m2": round(g.area), "geometry": mapping(spatial.to_wgs(g))}
    own_ids = {building["id"]} if building else set()
    for p in data.get("parcels") or []:
        if parcel and p["id"] == parcel["id"]:
            continue
        g = spatial.geojson_to_metric(p["geometry"])
        if g is None:
            continue
        built = any(bg.intersects(g) for _, bg in bgeoms)
        d = spatial.distance_m(origin, g)
        nearby_parcels.append({"id": p["id"], "section": p["section"], "numero": p["numero"], "surface_m2": p.get("contenance_m2") or round(g.area),
                               "built": built, "distance_m": round(d), "adjacent": parcel_geom is not None and g.touches(parcel_geom) or (parcel_geom is not None and g.distance(parcel_geom) < 0.5)})
    nearby_parcels.sort(key=lambda x: x["distance_m"])

    # ---- bâtiments voisins et densité
    neighbours = []
    for b, g in bgeoms:
        if building and b["id"] in own_ids:
            continue
        d = spatial.distance_m(origin, g)
        neighbours.append({"distance_m": round(d), "nature": b.get("nature"), "usage": b.get("usage_1"), "hauteur_m": b.get("hauteur"), "etages": b.get("nombre_d_etages"), "footprint_m2": round(g.area)})
    neighbours.sort(key=lambda x: x["distance_m"])
    disk250 = origin.buffer(r_local)
    built_area = sum(g.intersection(disk250).area for _, g in bgeoms)
    density = {"radius_m": r_local, "buildings": len([n for n in neighbours if n["distance_m"] <= r_local]), "built_ratio_pct": round(100 * built_area / disk250.area, 1),
               "within_50m": len([n for n in neighbours if n["distance_m"] <= radii[0]]), "nearest_m": neighbours[0]["distance_m"] if neighbours else None}

    def collect(key: str, extra=None) -> list[dict]:
        out = []
        for it in data.get(key) or []:
            r = _feat(it, origin, radii, lon, lat)
            if r:
                f, g = r
                if extra:
                    f.update(extra(f, g))
                out.append(f)
        out.sort(key=lambda x: x["distance_m"])
        return out

    # ---- routes (dédoublonnées par nom + importance)
    roads_all = collect("roads") + collect("roads_major")
    roads: dict[tuple, dict] = {}
    for r in roads_all:
        if r.get("nature") in ("Sentier", "Escalier", "Piste cyclable") or r.get("importance") in (None, "6"):
            continue
        k = (r.get("nom_collaboratif_gauche") or r.get("nature"), r.get("importance"))
        if k not in roads or r["distance_m"] < roads[k]["distance_m"]:
            roads[k] = {"name": r.get("nom_collaboratif_gauche"), "nature": r.get("nature"), "importance": r.get("importance"),
                        "importance_label": ROAD_IMPORTANCE.get(str(r.get("importance")), "non renseignée"), "lanes": r.get("nombre_de_voies"),
                        "speed_kmh": r.get("vitesse_moyenne_vl"), "distance_m": r["distance_m"], "ring": r["ring"], "direction": r["direction"], "source": "bdtopo"}
    roads_list = sorted(roads.values(), key=lambda x: (int(x["importance"] or 9), x["distance_m"]))
    railways = [{"nature": r.get("nature"), "electrified": r.get("electrifie"), "tracks": r.get("nombre_de_voies"), "max_speed": r.get("vitesse_maximale"),
                 "distance_m": r["distance_m"], "ring": r["ring"], "direction": r["direction"], "source": "bdtopo"} for r in collect("rail")][:5]
    rivers = {}
    for r in collect("rivers"):
        k = r.get("toponyme") or r["id"]
        if k not in rivers or r["distance_m"] < rivers[k]["distance_m"]:
            rivers[k] = {"name": r.get("toponyme"), "importance": r.get("importance"), "permanent": r.get("caractere_permanent"), "distance_m": r["distance_m"],
                         "ring": r["ring"], "direction": r["direction"], "type": "cours d'eau", "source": "bdtopo"}
    water = sorted(rivers.values(), key=lambda x: x["distance_m"])[:6] + [
        {"name": None, "nature": w.get("nature"), "distance_m": w["distance_m"], "ring": w["ring"], "direction": w["direction"], "type": "surface en eau", "source": "bdtopo"}
        for w in collect("water")[:4]]
    veg = collect("vegetation", lambda f, g: {"area_m2": round(g.area)})
    veg_ratio = round(100 * sum(spatial.geojson_to_metric(v["geometry"]).intersection(disk250).area for v in (data.get("vegetation") or []) if spatial.geojson_to_metric(v["geometry"]) is not None) / disk250.area, 1) if data.get("vegetation") is not None else None
    green = [{"nature": v.get("nature"), "area_m2": v["area_m2"], "distance_m": v["distance_m"], "ring": v["ring"], "direction": v["direction"], "source": "bdtopo"} for v in veg[:12]]
    forests = [v for v in veg if (v.get("nature") or "").startswith(("Forêt", "Bois"))]

    # ---- équipements (BD TOPO) + OSM
    services, industrial, sensitive, transport = [], [], [], []
    for z in collect("zai"):
        cat = z.get("categorie")
        item = {"name": z.get("toponyme"), "category": ZAI_SERVICE.get(cat, "autre"), "type": z.get("nature_detaillee") or z.get("nature"), "distance_m": z["distance_m"],
                "ring": z["ring"], "direction": z["direction"], "source": "bdtopo"}
        if cat == "Industriel et commercial":
            industrial.append(item)
        elif z.get("nature") in ("Hôpital", "Clinique", "Caserne de pompiers", "Prison", "Déchèterie", "Usine de traitement des eaux", "Station d'épuration"):
            sensitive.append(item)
            services.append(item)
        else:
            services.append(item)
    for t in collect("transport"):
        if t.get("nature") in ("Gare voyageurs et fret", "Gare voyageurs uniquement", "Station de métro", "Station de tramway", "Arrêt voyageurs"):
            transport.append({"name": t.get("toponyme"), "type": t.get("nature"), "distance_m": t["distance_m"], "ring": t["ring"], "direction": t["direction"], "source": "bdtopo"})
        elif t.get("nature") == "Parking":
            industrial.append({"name": t.get("toponyme"), "category": "parking", "type": "Parking", "distance_m": t["distance_m"], "ring": t["ring"], "direction": t["direction"], "source": "bdtopo"})
    for s in collect("sport"):
        services.append({"name": None, "category": "sport", "type": s.get("nature"), "distance_m": s["distance_m"], "ring": s["ring"], "direction": s["direction"], "source": "bdtopo"})
    aerodromes = [{"name": a.get("toponyme"), "type": a.get("nature"), "distance_m": a["distance_m"], "ring": a["ring"], "direction": a["direction"], "source": "bdtopo"} for a in collect("aerodrome")]
    osm_items = []
    for p in data.get("osm") or []:
        d = spatial.distance_m(origin, spatial.point_metric(p["lon"], p["lat"]))
        osm_items.append({"name": p.get("name"), "category": p["category"], "type": p["osm_tag"], "distance_m": round(d), "ring": spatial.ring_label(d, radii),
                          "direction": spatial.bearing_label(lon, lat, p["lon"], p["lat"]), "url": p["url"], "source": "osm"})
    osm_items.sort(key=lambda x: x["distance_m"])
    for it in osm_items:
        if it["category"] in ("transport", "gare"):
            transport.append(it)
        elif it["category"] == "nuisance":
            sensitive.append(it)
        elif it["category"] == "industrie":
            industrial.append(it)
        elif it["category"] == "espace_vert":
            green.append({"nature": it["name"] or "Parc / jardin", "area_m2": None, "distance_m": it["distance_m"], "ring": it["ring"], "direction": it["direction"], "source": "osm", "url": it["url"]})
        else:
            services.append(it)
    services.sort(key=lambda x: x["distance_m"])
    transport.sort(key=lambda x: x["distance_m"])
    industrial.sort(key=lambda x: x["distance_m"])
    green.sort(key=lambda x: x["distance_m"])

    # ---- terrain
    alti = data.get("alti")
    terrain = {"altitude_m": None, "slope_pct": None, "aspect": None, "landcover": None, "vegetation_ratio_250m_pct": veg_ratio}
    if alti:
        pts = []
        for e in alti:
            if e.get("z") is not None and e["z"] > -1000:
                m = spatial.point_metric(e["lon"], e["lat"])
                pts.append((m.x, m.y, float(e["z"])))
        if pts:
            terrain["altitude_m"] = round(pts[0][2], 1)
            terrain["slope_pct"], terrain["aspect"] = spatial.slope_aspect(pts)
            terrain["elevation_range_m"] = round(max(p[2] for p in pts) - min(p[2] for p in pts), 1)
    if data.get("clc"):
        from shapely.geometry import shape as _shape
        # le WFS filtre sur l'emprise des polygones : on garde celui qui contient réellement le point (coordonnées Lambert-93 natives)
        c = next((x for x in data["clc"] if _shape(x["geometry"]).contains(origin)), None) or min(data["clc"], key=lambda x: x.get("area_ha") or 1e12)
        terrain["landcover"] = {"code": c["code"], "label": c["label"], "source": "clc", "precision": "classe au 1/100 000 (unité minimale 25 ha) — ne décrit pas la parcelle"}
    nearest_water = min([w["distance_m"] for w in water], default=None)
    terrain["nearest_water_m"] = nearest_water
    terrain["nearest_forest_m"] = forests[0]["distance_m"] if forests else None

    # ---- urbanisme
    gpu = data.get("gpu")
    urbanism = None
    if gpu is not None:
        urbanism = {"zones": [{k: v for k, v in z.items() if k != "geometry"} for z in gpu["zones"]], "prescriptions": gpu["prescriptions"][:20], "infos": gpu["infos"][:20],
                    "servitudes": gpu["servitudes"][:20], "documents": data.get("gpu_docs") or [], "source": "gpu",
                    "notice": "Zonage et prescriptions tels que publiés sur le GPU. Toute interprétation du règlement doit être vérifiée auprès de la collectivité."}
        zone_types = {z.get("typezone") for z in gpu["zones"]}
        urbanism["summary"] = {"typezone": sorted(t for t in zone_types if t), "constructible_hint": "U" in zone_types or "AU" in zone_types,
                               "agricole_ou_naturel": bool(zone_types & {"A", "N"})}

    # ---- risques (Géorisques, déjà normalisés)
    risk_out = None
    if risks:
        items = risks.get("items") or []
        risk_out = {"at_address": [i for i in items if i.get("present") and i.get("scope") == "adresse"],
                    "commune_only": [i for i in items if i.get("present") and i.get("scope") != "adresse"],
                    "argile": risks.get("argile"), "radon": risks.get("radon"), "catnat": risks.get("catnat"), "icpe": risks.get("icpe"),
                    "partial": risks.get("partial"), "fetched_at": risks.get("fetched_at"), "source_url": risks.get("source_url"), "source": "georisques"}
        if risks.get("fetched_at"):
            sources.append({"id": "georisques", "name": "Géorisques (BRGM / MTE)", "kind": "official", "licence": "Licence Ouverte 2.0", "doc_url": "https://www.georisques.gouv.fr/",
                            "request_url": risks.get("source_url"), "fetched_at": str(risks["fetched_at"]), "status": "partial" if risks.get("partial") else "ok", "what": "Risques naturels et technologiques"})
    else:
        unavailable.append("Risques (Géorisques)")

    # ---- nuisances potentielles (factuelles)
    nuisances = []
    for r in roads_list:
        if r["importance"] in ("1", "2", "3") and r["distance_m"] <= rmax:
            nuisances.append({"type": "route", "label": f"{r['name'] or r['nature']} ({r['importance_label']})", "distance_m": r["distance_m"], "source": "bdtopo"})
    for r in railways[:1]:
        nuisances.append({"type": "voie ferrée", "label": r["nature"] or "Voie ferrée", "distance_m": r["distance_m"], "source": "bdtopo"})
    for i in industrial[:5]:
        nuisances.append({"type": "activité", "label": i["name"] or i["type"], "distance_m": i["distance_m"], "source": i["source"]})
    for a in aerodromes[:2]:
        nuisances.append({"type": "aérodrome", "label": a["name"] or a["type"], "distance_m": a["distance_m"], "source": "bdtopo"})
    for s in sensitive[:5]:
        nuisances.append({"type": "établissement", "label": s["name"] or s["type"], "distance_m": s["distance_m"], "source": s["source"]})
    nuisances.sort(key=lambda x: x["distance_m"])

    rings = []
    for i, r in enumerate(radii):
        lo = radii[i - 1] if i else 0
        inr = lambda lst: [x for x in lst if lo < x["distance_m"] <= r]  # noqa: E731
        rings.append({"label": spatial.ring_label(r, radii), "min_m": lo, "max_m": r, "buildings": len(inr(neighbours)), "roads": len(inr(roads_list)),
                      "services": len(inr(services)), "transport": len(inr(transport)), "green": len(inr(green)), "water": len(inr(water)),
                      "industrial": len(inr(industrial)), "unbuilt_parcels": len([p for p in nearby_parcels if not p["built"] and lo < p["distance_m"] <= r])})

    return {
        "generated_at": _utc(), "radii_m": radii,
        "address": {"input": address, "label": (geo or {}).get("label") or address, "precision": (geo or {}).get("precision"), "score": (geo or {}).get("score"), "code_insee": code_insee, "source": "ban"},
        "coordinates": {"lon": lon, "lat": lat, "crs": "EPSG:4326", "metric_crs": "EPSG:2154"},
        "parcel": {k: v for k, v in (parcel or {}).items()} if parcel else None,
        "building": building,
        "neighbours": neighbours[:30], "density": density,
        "terrain": terrain, "urbanism": urbanism, "risks": risk_out,
        "roads": roads_list[:25], "railways": railways, "water": water, "green_spaces": green[:20], "services": services[:60], "transport": transport[:20],
        "industrial_sites": industrial[:15], "aerodromes": aerodromes, "nuisances": nuisances[:15], "nearby_parcels": nearby_parcels[:40],
        "rings": rings, "sources": sources, "unavailable": sorted(set(unavailable)),
        "limits": ["Distances à vol d'oiseau (Lambert-93), pas d'itinéraire piéton ou routier.",
                   "Aucune mesure acoustique : la présence d'une infrastructure à une distance donnée ne permet pas de conclure sur le bruit réel.",
                   "Pente et orientation calculées sur 9 points du MNT (pas de 25 m) : indicatives, l'ensoleillement réel n'est pas évalué.",
                   "Occupation du sol CLC au 1/100 000 : contexte paysager, pas la parcelle.",
                   "Services OpenStreetMap : exhaustivité non garantie, sous licence ODbL."],
    }
