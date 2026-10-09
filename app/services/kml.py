from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon


KML_NS = "http://www.opengis.net/kml/2.2"


def _strip(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _coords(text: str | None):
    if not text:
        return []
    result = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        lon = float(parts[0])
        lat = float(parts[1])
        alt = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0
        result.append((lon, lat, alt))
    return result


def _find_child(parent: ET.Element, name: str):
    for child in parent:
        if _strip(child.tag) == name:
            return child
    return None


def _find_children(parent: ET.Element, name: str):
    return [child for child in parent.iter() if _strip(child.tag) == name]


def _geometry(element: ET.Element):
    name = _strip(element.tag)

    if name == "Point":
        coords = _coords((_find_child(element, "coordinates").text if _find_child(element, "coordinates") is not None else None))
        return Point(coords[0]) if coords else None

    if name == "LineString":
        coords_node = _find_child(element, "coordinates")
        coords = _coords(coords_node.text if coords_node is not None else None)
        return LineString(coords) if len(coords) >= 2 else None

    if name == "Polygon":
        outer = _find_child(element, "outerBoundaryIs")
        if outer is None:
            outer = _find_child(element, "outerBoundary")
        outer_ring = _find_child(outer, "LinearRing") if outer is not None else None
        outer_coords_node = _find_child(outer_ring, "coordinates") if outer_ring is not None else None
        outer_coords = _coords(outer_coords_node.text if outer_coords_node is not None else None)
        if len(outer_coords) < 4:
            return None

        holes = []
        for inner in (_find_children(element, "innerBoundaryIs") + _find_children(element, "innerBoundary")):
            ring = _find_child(inner, "LinearRing")
            coords_node = _find_child(ring, "coordinates") if ring is not None else None
            coords = _coords(coords_node.text if coords_node is not None else None)
            if len(coords) >= 4:
                holes.append(coords)
        return Polygon(outer_coords, holes)

    if name == "MultiGeometry":
        geoms = []
        for child in element:
            geom = _geometry(child)
            if geom is not None:
                geoms.append(geom)
        if not geoms:
            return None
        types = {g.geom_type for g in geoms}
        if types <= {"Point"}:
            return MultiPoint(geoms)
        if types <= {"LineString"}:
            return MultiLineString(geoms)
        if types <= {"Polygon"}:
            return MultiPolygon(geoms)
        return GeometryCollection(geoms)

    return None


def parse_kml(path: Path) -> list[dict[str, Any]]:
    tree = ET.parse(path)
    root = tree.getroot()
    features = []

    for placemark in [e for e in root.iter() if _strip(e.tag) == "Placemark"]:
        name_node = _find_child(placemark, "name")
        name = name_node.text.strip() if name_node is not None and name_node.text else None

        description_node = _find_child(placemark, "description")
        description = description_node.text.strip() if description_node is not None and description_node.text else None

        geom = None
        for child in placemark:
            candidate = _geometry(child)
            if candidate is not None:
                geom = candidate
                break

        if geom is None:
            continue

        properties = {}
        if name:
            properties["name"] = name
        if description:
            properties["description"] = description

        extended = _find_child(placemark, "ExtendedData")
        if extended is not None:
            for data in _find_children(extended, "Data"):
                key = data.attrib.get("name")
                value_node = _find_child(data, "value")
                if key and value_node is not None:
                    properties[key] = value_node.text

        features.append({
            "feature_id": name or str(len(features)),
            "geometry": geom,
            "properties": properties,
        })

    return features
