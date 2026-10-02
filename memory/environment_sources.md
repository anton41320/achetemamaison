# Analyse de l'environnement — sources et API utilisées

Vérifiées depuis le serveur le 2026-10-02. Tous les appels passent par `environment/sources.fetch_json` (cache Mongo `env_cache`, 30 j ; `fetched_at` journalisé ; `status=unavailable` en cas d'échec — jamais de donnée inventée).

| Module | Source | Endpoint | Paramètres | Retour | Licence | Limites |
|---|---|---|---|---|---|---|
| `official.geocode` | BAN (Géoplateforme, secours api-adresse) | `GET https://data.geopf.fr/geocodage/search` | `q`, `limit=1` | GeoJSON : lon/lat, `citycode`, `score`, `type` (housenumber/street…) | Licence Ouverte | précision = `type` |
| `official.parcels` | Cadastre (API Carto IGN / DGFiP) | `GET https://apicarto.ign.fr/api/cadastre/parcelle` | `geom` (GeoJSON polygone), `_limit` | parcelles : `section`, `numero`, `contenance`, `code_insee`, géométrie | Licence Ouverte | 500 max par appel ; emprise ≈ 120 m |
| `official.topo_layer` | IGN BD TOPO v3 (WFS) | `GET https://data.geopf.fr/wfs/ows` `TYPENAMES=BDTOPO_V3:<couche>` | `BBOX` (lat,lon ordre EPSG:4326) ou `CQL_FILTER=… AND BBOX(geometrie,lon,lat,…)` | GeoJSON ; couches : batiment, troncon_de_route (importance 1–6, nature), troncon_de_voie_ferree, cours_d_eau, surface_hydrographique, zone_de_vegetation, zone_d_activite_ou_d_interet (categorie/nature), aerodrome, equipement_de_transport (gares, parkings), terrain_de_sport | Licence Ouverte | `COUNT` plafonné ; importance = hiérarchie fonctionnelle, pas administrative |
| `official.elevation_grid` | IGN RGE ALTI (service altimétrique) | `GET https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json` | `lon|lat` (9 points, pas 25 m), `resource=ign_rge_alti_wld` | `elevations[].z` | Licence Ouverte | pente/orientation par ajustement de plan — indicatif |
| `official.landcover` | Corine Land Cover 2018 (WFS IGN) | `TYPENAMES=LANDCOVER.CLC18_FR:clc18_fr`, `BBOX` lon,lat | `code_18` | Licence Ouverte | unité minimale 25 ha : contexte paysager, pas la parcelle |
| `official.gpu_point` | Géoportail de l'Urbanisme | `GET https://www.geoportail-urbanisme.gouv.fr/api/feature-info/du` | `lon`, `lat` | features `zone_urba` (libelle, libelong, typezone, nomfic), `prescription_*`, `info_*`, SUP, `document` | Licence Ouverte | ~6 s ; le WFS `wfs_du:*` et apicarto/gpu étaient en erreur (pool DB) → non utilisés |
| `official.gpu_documents` | GPU | `GET https://www.geoportail-urbanisme.gouv.fr/api/document` | `grid_name=<INSEE>`, `status=document.production` | documents en vigueur (type, dates, id) | Licence Ouverte | lien `document/by-id/<id>` |
| `georisques` (existant) | Géorisques | `/api/v1/resultats_rapport_risque`, `/rga`, `/radon`, `/gaspar/catnat`, `/installations_classees` | `latlon`, `code_insee` | risques à l'adresse / commune, argile, radon, CatNat, ICPE | Licence Ouverte | indisponible par moments → `risks=null` signalé |
| `osm.pois` | OpenStreetMap (Overpass) | `POST https://overpass.openstreetmap.fr/api/interpreter` (secours overpass-api.de) | requête `around:<r>` sur amenity/shop/highway/railway/leisure/landuse | POI : nom, tag, coordonnées, lien osm.org | **ODbL** (attribution affichée) | exhaustivité non garantie |

Non intégrés au MVP (signalés « non consultés ») : ADEME DPE, Météo-France, données des collectivités, itinéraires piétons (distances à vol d'oiseau uniquement).

## Calculs (remplacent PostGIS) — `environment/spatial.py`
Projection Lambert-93 (EPSG:2154) via pyproj ; distances/intersections/aires shapely ; emprises géodésiques ; densité bâtie = Σ emprises ∩ disque 250 m / aire du disque ; parcelles non bâties = parcelles sans intersection avec un bâtiment BD TOPO.

## Ajustements d'estimation — `environment/valuation.py`
Facteurs de micro-localisation bornés à [−6 %, +4 %] (autoroute/axe principal/voie ferrée/industrie/aérodrome/inondation/argile en négatif ; eau, espaces verts, école, commerces, bus, gare en positif), chacun libellé avec sa source. Appliqués dans `server._run_estimation` quand `env_analyses` contient l'analyse du bien.
