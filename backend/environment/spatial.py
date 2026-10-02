"""Moteur spatial (remplace PostGIS) : projection Lambert-93, distances géodésiques, intersections, emprises."""
from __future__ import annotations

import math
from typing import Iterable, Optional

from pyproj import Geod, Transformer
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

GEOD = Geod(ellps="WGS84")
_TO_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
_TO_WGS = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def to_metric(geom: BaseGeometry) -> BaseGeometry:
    return transform(_TO_L93.transform, geom)


def to_wgs(geom: BaseGeometry) -> BaseGeometry:
    return transform(_TO_WGS.transform, geom)


def geojson_to_metric(geometry: dict) -> Optional[BaseGeometry]:
    try:
        g = shape(geometry)
    except Exception:  # noqa: BLE001
        return None
    if g.is_empty:
        return None
    g = to_metric(g)
    return g if g.is_valid else g.buffer(0)


def point_metric(lon: float, lat: float) -> Point:
    return to_metric(Point(lon, lat))


def distance_m(origin: Point, geom: BaseGeometry) -> float:
    """Distance plane Lambert-93 (erreur < 0,1 % en France métropolitaine)."""
    return float(origin.distance(geom))


def bbox_around(lon: float, lat: float, radius_m: float) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) englobant le cercle de rayon radius_m."""
    _, north, _ = GEOD.fwd(lon, lat, 0, radius_m)
    east, _, _ = GEOD.fwd(lon, lat, 90, radius_m)
    _, south, _ = GEOD.fwd(lon, lat, 180, radius_m)
    west, _, _ = GEOD.fwd(lon, lat, 270, radius_m)
    return (west, south, east, north)


def bearing_label(lon0: float, lat0: float, lon1: float, lat1: float) -> str:
    az, _, _ = GEOD.inv(lon0, lat0, lon1, lat1)
    dirs = ["nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest"]
    return dirs[int(((az % 360) + 22.5) // 45) % 8]


def ring_label(d: float, radii: Iterable[int]) -> str:
    prev = 0
    for r in radii:
        if d <= r:
            return f"{prev}–{r} m" if r < 1000 else f"{prev / 1000:g}–{r / 1000:g} km".replace("0–", "0–")
        prev = r
    return f"> {prev / 1000:g} km"


def slope_aspect(grid: list[tuple[float, float, float]]) -> tuple[Optional[float], Optional[str]]:
    """Pente (%) et orientation à partir de 9 points (x, y métriques, z). Ajustement d'un plan par moindres carrés."""
    pts = [p for p in grid if p[2] is not None and p[2] > -1000]
    if len(pts) < 4:
        return None, None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    mz = sum(p[2] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    sxz = sum((p[0] - mx) * (p[2] - mz) for p in pts)
    syz = sum((p[1] - my) * (p[2] - mz) for p in pts)
    det = sxx * syy - sxy * sxy
    if abs(det) < 1e-9:
        return None, None
    a = (sxz * syy - syz * sxy) / det  # dz/dx
    b = (syz * sxx - sxz * sxy) / det  # dz/dy
    slope_pct = math.hypot(a, b) * 100
    if slope_pct < 1.0:
        return round(slope_pct, 1), "terrain plat"
    az = (math.degrees(math.atan2(-a, -b)) + 360) % 360  # direction descendante
    dirs = ["nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest"]
    return round(slope_pct, 1), f"pente exposée {dirs[int((az + 22.5) // 45) % 8]}"
