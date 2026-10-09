from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

import geopandas as gpd


def safe_extract_zip(
    zip_path: Path,
    destination: Path,
    max_files: int,
    max_unzipped_bytes: int,
) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > max_files:
            raise ValueError(f"Archive contains more than {max_files} files.")

        total_size = sum(info.file_size for info in infos)
        if total_size > max_unzipped_bytes:
            raise ValueError("Uncompressed archive exceeds the configured size limit.")

        for info in infos:
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("Unsafe archive path detected.")
            if info.is_dir():
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def read_shapefile(zip_path: Path, work_dir: Path):
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(zip_path, extract_dir, max_files=100, max_unzipped_bytes=200 * 1024 * 1024)

    shp_files = list(extract_dir.rglob("*.shp"))
    if len(shp_files) != 1:
        raise ValueError("ZIP must contain exactly one .shp file.")

    shp = shp_files[0]
    siblings = {p.suffix.lower() for p in shp.parent.iterdir() if p.is_file() and p.stem == shp.stem}
    if ".shx" not in siblings or ".dbf" not in siblings:
        raise ValueError("Shapefile ZIP must include .shp, .shx and .dbf files.")

    gdf = gpd.read_file(shp, engine="pyogrio")
    return gdf
