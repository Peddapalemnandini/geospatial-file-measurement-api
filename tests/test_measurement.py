from shapely.geometry import LineString, Polygon
from pyproj import CRS

from app.services.measurement import measure_geometry


def test_polygon_area_in_projected_crs():
    polygon = Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])
    result = measure_geometry(polygon, CRS.from_epsg(32643))
    assert result.supported is True
    assert result.kind == "area"
    assert abs(result.value - 1_000_000) < 1


def test_line_length_in_projected_crs():
    line = LineString([(0, 0), (300, 400)])
    result = measure_geometry(line, CRS.from_epsg(32643))
    assert result.supported is True
    assert result.kind == "length"
    assert abs(result.value - 500) < 0.001


def test_missing_crs_is_rejected_for_measurement():
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    result = measure_geometry(polygon, None)
    assert result.supported is False
    assert "CRS" in result.note
