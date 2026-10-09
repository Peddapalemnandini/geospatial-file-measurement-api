from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
from pyproj import CRS, Transformer
from shapely import force_2d
from shapely.geometry import GeometryCollection, MultiLineString, MultiPoint, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform
from shapely.validation import explain_validity

try:
    from shapely import make_valid
except ImportError:
    make_valid = None


@dataclass
class MeasurementResult:
    supported: bool
    kind: str | None
    value: float | None
    unit: str | None
    measurement_crs: str | None
    note: str | None


def _safe_centroid_lon_lat(geometry: BaseGeometry, source_crs: CRS) -> tuple[float, float]:
    """Return a representative lon/lat point for local projection creation."""
    geom = geometry
    if source_crs != CRS.from_epsg(4326):
        transformer = Transformer.from_crs(source_crs, 4326, always_xy=True)
        geom = transform(transformer.transform, geom)
    point = geom.representative_point()
    return float(point.x), float(point.y)


def _local_crs(geometry: BaseGeometry, source_crs: CRS, kind: str) -> CRS:
    lon, lat = _safe_centroid_lon_lat(geometry, source_crs)
    if kind == "area":
        return CRS.from_proj4(
            f"+proj=laea +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
        )
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
    )


def _project(geometry: BaseGeometry, source_crs: CRS, target_crs: CRS) -> BaseGeometry:
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transform(transformer.transform, geometry)


def _projected_source_is_measurement_safe(crs: CRS) -> bool:
    if not crs.is_projected:
        return False
    # Web Mercator is not appropriate for ground measurements.
    if crs.to_epsg() == 3857:
        return False
    try:
        units = crs.axis_info[0].unit_name.lower()
        return "metre" in units or "meter" in units or "foot" in units
    except (IndexError, AttributeError):
        return False


def _to_meters_factor(crs: CRS) -> float:
    try:
        unit_name = crs.axis_info[0].unit_name.lower()
        if "foot" in unit_name:
            # Convert international/survey foot to metres using pyproj's unit conversion.
            factor = crs.axis_info[0].unit_conversion_factor
            return float(factor)
    except (IndexError, AttributeError):
        pass
    return 1.0


def _repair(geometry: BaseGeometry) -> BaseGeometry:
    if geometry.is_valid:
        return geometry
    if make_valid is not None:
        return make_valid(geometry)
    return geometry.buffer(0)


def measure_geometry(geometry: BaseGeometry, source_crs: CRS | None) -> MeasurementResult:
    if geometry is None or geometry.is_empty:
        return MeasurementResult(False, None, None, None, None, "Empty geometry cannot be measured.")

    geometry = force_2d(geometry)

    if isinstance(geometry, (Point, MultiPoint)):
        return MeasurementResult(
            True, None, None, None, None,
            "Point geometries do not have an area or a length.",
        )

    if isinstance(geometry, GeometryCollection):
        return MeasurementResult(
            False, None, None, None, None,
            "GeometryCollection is not supported for measurement.",
        )

    is_area = geometry.geom_type in {"Polygon", "MultiPolygon"}
    is_length = geometry.geom_type in {"LineString", "MultiLineString"}

    if not (is_area or is_length):
        return MeasurementResult(
            False, None, None, None, None,
            f"Geometry type {geometry.geom_type} is not supported for measurement.",
        )

    if source_crs is None:
        return MeasurementResult(
            False, "area" if is_area else "length", None, None, None,
            "A CRS is required for accurate measurement. Provide a .prj file for shapefiles.",
        )

    source_crs = CRS.from_user_input(source_crs)
    geometry = _repair(geometry)

    if geometry.is_empty:
        return MeasurementResult(False, None, None, None, None, "Geometry became empty after repair.")

    if _projected_source_is_measurement_safe(source_crs):
        target_crs = source_crs
    else:
        target_crs = _local_crs(geometry, source_crs, "area" if is_area else "length")

    projected = _project(geometry, source_crs, target_crs)
    factor = _to_meters_factor(target_crs)

    if is_area:
        value = float(projected.area) * factor * factor
        return MeasurementResult(
            True, "area", value, "square_meters", target_crs.to_string(),
            f"Area calculated after transforming to a local equal-area CRS. "
            f"Source CRS: {source_crs.to_string()}.",
        )

    value = float(projected.length) * factor
    return MeasurementResult(
        True, "length", value, "meters", target_crs.to_string(),
        f"Length calculated after transforming to a local distance-preserving CRS. "
        f"Source CRS: {source_crs.to_string()}.",
    )
