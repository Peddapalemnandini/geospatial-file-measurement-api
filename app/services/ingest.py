from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import geopandas as gpd
from shapely.geometry import mapping
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Feature, UploadedFile
from app.services.kml import parse_kml
from app.services.measurement import measure_geometry
from app.services.shapefile import safe_extract_zip


ALLOWED_EXTENSIONS = {".zip", ".kml", ".kmz"}


def _safe_filename(filename: str) -> str:
    return Path(filename).name or "upload"


def _detect_zip_type(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        names = [n.lower() for n in zf.namelist() if not n.endswith("/")]
    if any(n.endswith(".shp") for n in names):
        return "shapefile"
    if any(n.endswith(".kml") for n in names):
        return "kmz"
    raise ValueError("ZIP must contain a shapefile or KML file.")


def _read_zip(zip_path: Path, work_dir: Path):
    file_type = _detect_zip_type(zip_path)
    if file_type == "shapefile":
        extract_dir = work_dir / "shape"
        safe_extract_zip(
            zip_path,
            extract_dir,
            settings.max_zip_files,
            settings.max_unzipped_bytes,
        )
        shp_files = list(extract_dir.rglob("*.shp"))
        if len(shp_files) != 1:
            raise ValueError("ZIP must contain exactly one .shp file.")
        shp = shp_files[0]
        siblings = {p.suffix.lower() for p in shp.parent.iterdir() if p.is_file() and p.stem == shp.stem}
        if ".shx" not in siblings or ".dbf" not in siblings:
            raise ValueError("Shapefile ZIP must include .shp, .shx and .dbf files.")
        gdf = gpd.read_file(shp, engine="pyogrio")
        return file_type, gdf

    extract_dir = work_dir / "kml"
    safe_extract_zip(
        zip_path,
        extract_dir,
        settings.max_zip_files,
        settings.max_unzipped_bytes,
    )
    kml_files = list(extract_dir.rglob("*.kml"))
    if len(kml_files) != 1:
        raise ValueError("KMZ-style ZIP must contain exactly one .kml file.")
    return file_type, parse_kml(kml_files[0])


def _gdf_features(gdf):
    crs = gdf.crs
    result = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        props = {}
        for key, value in row.drop(labels=["geometry"]).items():
            if value is None:
                props[str(key)] = None
            elif hasattr(value, "item"):
                try:
                    props[str(key)] = value.item()
                except Exception:
                    props[str(key)] = str(value)
            else:
                try:
                    json.dumps(value)
                    props[str(key)] = value
                except TypeError:
                    props[str(key)] = str(value)

        result.append({
            "feature_id": str(props.get("id") or props.get("fid") or props.get("name") or idx),
            "geometry": geom,
            "properties": props,
        })
    return result, crs


def process_upload(
    db: Session,
    filename: str,
    content: bytes,
) -> UploadedFile:
    original_name = _safe_filename(filename)
    suffix = Path(original_name).suffix.lower()

    if not content:
        raise ValueError("Empty file.")
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .zip, .kml and .kmz files are supported.")
    if len(content) > settings.max_upload_bytes:
        raise OverflowError("Upload exceeds the configured maximum size.")

    upload_id = str(uuid4())
    upload_dir = Path(settings.upload_dir) / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_path = upload_dir / original_name
    original_path.write_bytes(content)

    work_dir = upload_dir / "work"
    work_dir.mkdir(exist_ok=True)

    try:
        if suffix == ".kml":
            file_type = "kml"
            raw_features = parse_kml(original_path)
            source_crs = "EPSG:4326"
            crs_obj = "EPSG:4326"
        elif suffix == ".kmz":
            file_type, raw = _read_zip(original_path, work_dir)
            raw_features = raw
            source_crs = "EPSG:4326"
            crs_obj = "EPSG:4326"
        else:
            file_type, raw = _read_zip(original_path, work_dir)
            if not hasattr(raw, "crs"):
                raise ValueError("Unexpected geospatial data.")
            raw_features, crs_obj = _gdf_features(raw)
            source_crs = crs_obj.to_string() if crs_obj else None

        if len(raw_features) > settings.max_features:
            raise OverflowError("Feature count exceeds the configured maximum.")

        record = UploadedFile(
            id=upload_id,
            filename=original_name,
            file_type=file_type,
            crs=source_crs,
            feature_count=len(raw_features),
            status="PROCESSING",
            storage_path=str(original_path),
        )
        db.add(record)
        db.flush()

        for index, item in enumerate(raw_features):
            geom = item["geometry"]
            result = measure_geometry(geom, crs_obj)
            feature = Feature(
                file_id=upload_id,
                feature_index=index,
                feature_id=str(item["feature_id"]),
                geometry_type=geom.geom_type,
                geometry_json=json.dumps(mapping(geom)),
                properties_json=json.dumps(item["properties"], default=str),
                measurement_json=json.dumps({
                    "supported": result.supported,
                    "kind": result.kind,
                    "value": result.value,
                    "unit": result.unit,
                    "measurement_crs": result.measurement_crs,
                    "note": result.note,
                }),
            )
            db.add(feature)

        record.status = "COMPLETED"
        db.commit()
        db.refresh(record)
        shutil.rmtree(work_dir, ignore_errors=True)
        return record

    except Exception:
        db.rollback()
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise
