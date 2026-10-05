"""Tests unitaires du moteur spatial et des ajustements environnement (sans réseau)."""
import math

from shapely.geometry import LineString, Point

from environment import spatial, valuation
from environment.report import _parse


def test_metric_distance_matches_geodesic():
    lon, lat = 1.3357, 47.5864
    east, _, _ = spatial.GEOD.fwd(lon, lat, 90, 500)
    origin = spatial.point_metric(lon, lat)
    d = spatial.distance_m(origin, spatial.point_metric(east, lat))
    assert abs(d - 500) < 1.0


def test_geojson_to_metric_and_distance_to_line():
    lon, lat = 1.3357, 47.5864
    _, north, _ = spatial.GEOD.fwd(lon, lat, 0, 120)
    line = {"type": "LineString", "coordinates": [[lon - 0.01, north], [lon + 0.01, north]]}
    g = spatial.geojson_to_metric(line)
    assert isinstance(g, LineString)
    assert abs(spatial.distance_m(spatial.point_metric(lon, lat), g) - 120) < 1.0


def test_bbox_and_bearing():
    w, s, e, n = spatial.bbox_around(1.3357, 47.5864, 1000)
    assert w < 1.3357 < e and s < 47.5864 < n
    assert spatial.bearing_label(1.3357, 47.5864, 1.3357, 47.60) == "nord"
    assert spatial.bearing_label(1.3357, 47.5864, 1.36, 47.5864) == "est"


def test_ring_labels():
    radii = [50, 250, 1000, 5000]
    assert spatial.ring_label(10, radii) == "0–50 m"
    assert spatial.ring_label(120, radii) == "50–250 m"
    assert spatial.ring_label(3000, radii) == "1–5 km"
    assert spatial.ring_label(9000, radii) == "> 5 km"


def test_slope_aspect_plane():
    # plan incliné de 10 % descendant vers le sud (z diminue quand y diminue)
    grid = [(x, y, 100 + 0.10 * y) for x in (-25, 0, 25) for y in (-25, 0, 25)]
    slope, aspect = spatial.slope_aspect(grid)
    assert math.isclose(slope, 10.0, abs_tol=0.1)
    assert aspect == "pente exposée sud"
    flat, label = spatial.slope_aspect([(x, y, 50.0) for x in (-25, 0, 25) for y in (-25, 0, 25)])
    assert flat == 0.0 and label == "terrain plat"


def test_environment_adjustments_bounded_and_sourced():
    env = {
        "roads": [{"importance": "1", "distance_m": 100}, {"importance": "2", "distance_m": 40}],
        "railways": [{"nature": "Voie ferrée principale", "distance_m": 100}],
        "industrial_sites": [{"category": "industrie", "distance_m": 100}],
        "aerodromes": [{"distance_m": 3000}],
        "risks": {"at_address": [{"key": "inondation", "level": "high"}], "argile": {"level": "high"}},
        "terrain": {"nearest_water_m": 50, "nearest_forest_m": None},
        "green_spaces": [], "services": [], "transport": [],
    }
    adj = valuation.environment_adjustments(env, 200_000)
    total = sum(a.pct for a in adj)
    assert math.isclose(total, valuation.CAP_LOW, abs_tol=1e-6)  # plafonné à -6 %
    assert all(a.key.startswith("env_") for a in adj)
    assert any("BD TOPO" in a.label or "Géorisques" in a.label for a in adj)
    positive = valuation.environment_adjustments({"roads": [], "railways": [], "industrial_sites": [], "aerodromes": [], "risks": None,
                                                  "terrain": {"nearest_water_m": 100, "nearest_forest_m": 100},
                                                  "green_spaces": [{"distance_m": 100}],
                                                  "services": [{"category": "ecole", "distance_m": 200}, *[{"category": "commerce", "distance_m": 300}] * 3],
                                                  "transport": [{"category": "transport", "distance_m": 100}, {"category": "gare", "distance_m": 800}]}, 200_000)
    assert math.isclose(sum(a.pct for a in positive), valuation.CAP_HIGH, abs_tol=1e-6)  # plafonné à +4 %


def test_report_parse_tolerates_fences_and_missing_keys():
    out = _parse('```json\n{"resume": "ok", "a_verifier": ["x", "y"]}\n```')
    assert out["resume"] == "ok" and out["a_verifier"] == ["x", "y"]
    assert out["risques"].startswith("Non disponible")


def test_listing_highlights_prioritized_and_capped():
    from environment.listing_facts import facts_block, neighbourhood_highlights
    env = {
        "services": [{"category": "culture", "name": "Musée", "distance_m": 90, "source": "bdtopo"}, {"category": "sante", "name": "Dr X", "distance_m": 80, "source": "osm"},
                     {"category": "ecole", "name": "École Jules Ferry", "distance_m": 210, "source": "bdtopo"}, {"category": "commerce", "name": "Boulangerie", "distance_m": 260, "source": "osm"},
                     {"category": "commerce", "name": "Épicerie", "distance_m": 340, "source": "osm"}, {"category": "sport", "distance_m": 110, "source": "bdtopo"},
                     {"category": "service_public", "name": "Poste", "distance_m": 160, "source": "bdtopo"}],
        "transport": [{"category": "transport", "distance_m": 120, "source": "osm"}, {"category": "gare", "name": "Gare de Blois", "distance_m": 1800, "source": "bdtopo"}],
        "green_spaces": [{"nature": "Bois", "distance_m": 34, "source": "bdtopo"}], "water": [{"name": "Canal de Berry", "type": "cours d'eau", "distance_m": 12}],
        "terrain": {"nearest_forest_m": 34}, "risks": {"at_address": []},
    }
    hl = neighbourhood_highlights(env)
    assert len(hl) == 5 and [h["key"] for h in hl] == ["ecole", "commerce", "gare", "bus", "vert"]
    assert "Dr X" not in facts_block(env)  # pas de nom de professionnel de santé
    assert "2 commerces alimentaires à moins de 340 m" in facts_block(env)
    assert neighbourhood_highlights({"services": [], "transport": [], "green_spaces": [], "water": [], "terrain": {}}) == [] and facts_block({"services": []}) is None


def test_pdf_environment_section_builds_without_crash():
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Table

    from environment.pdf import environment_section
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9)
    small = ParagraphStyle("s", parent=body, fontSize=8)
    env_doc = {"created_at": "2026-10-02T12:00:00", "analysis": {
        "generated_at": "2026-10-02T12:00:00+00:00", "parcel": {"section": "AO", "numero": "0329", "contenance_m2": 14080}, "building": {"footprint_m2": 22},
        "density": {"built_ratio_pct": 9.5, "buildings": 361, "nearest_m": 1}, "terrain": {"altitude_m": 93.6, "slope_pct": 5.1, "aspect": "pente exposée sud", "landcover": {"label": "Prairies"}},
        "green_spaces": [{"nature": "Bois", "distance_m": 34, "direction": "nord", "source": "bdtopo"}], "water": [], "roads": [{"name": "D 976", "importance_label": "axe principal", "distance_m": 76, "direction": "est", "source": "bdtopo"}],
        "railways": [], "transport": [], "services": [{"name": "École <Jules & Ferry>", "category": "ecole", "distance_m": 210, "direction": "sud", "source": "bdtopo"}],
        "nuisances": [{"label": "Voie ferrée", "type": "voie ferrée", "distance_m": 253, "source": "bdtopo"}],
        "risks": {"at_address": [{"label": "Pollution des sols", "level": "info"}], "commune_only": [{"label": "Séisme"}]},
        "urbanism": {"zones": [{"libelle": "N", "typezone": "N", "reglement": "41039_reglement.pdf"}], "servitudes": [{"libelle": "A4"}], "prescriptions": [], "notice": "Vérifier."},
        "nearby_parcels": [{"section": "AO", "numero": "0328", "surface_m2": 604, "built": False, "distance_m": 9, "adjacent": True}],
        "sources": [{"id": "bdtopo", "name": "IGN BD TOPO", "kind": "official", "licence": "LO 2.0", "fetched_at": "2026-10-02T12:00:00+00:00", "status": "ok"}],
        "limits": ["Distances à vol d'oiseau."]},
        "report": {"sections": {"resume": "Texte <b>", "nuisances": "N", "a_verifier": ["Vérifier X"]}, "titles": {"resume": "Résumé"}, "disclaimer": "IA."}}
    flow = environment_section(env_doc, ParagraphStyle("h2", parent=ss["Heading2"]), body, small, lambda rows, widths, style: Table(rows, colWidths=widths))
    assert len(flow) > 20
    # rendu effectif (échappement XML des « < » et « & »)
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate
    SimpleDocTemplate(BytesIO(), pagesize=A4).build(flow)
