from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Feature, UploadedFile
from app.schemas import FileListResponse, FeatureResponse, MeasurementsResponse, Measurement, UploadResponse
from app.services.ingest import process_upload


router = APIRouter(prefix="/api/files", tags=["files"])


def _upload_response(item: UploadedFile) -> UploadResponse:
    return UploadResponse(
        id=item.id,
        filename=item.filename,
        feature_count=item.feature_count,
        crs=item.crs,
        status=item.status,
        file_type=item.file_type,
        created_at=item.created_at,
    )


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()

    try:
        record = process_upload(db, file.filename or "upload", content)
    except OverflowError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Unable to read geospatial data: {exc}")

    return _upload_response(record)


@router.get("/", response_model=FileListResponse)
def list_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(UploadedFile)
        .order_by(UploadedFile.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return FileListResponse(
        items=[_upload_response(row) for row in rows],
        limit=limit,
        offset=offset,
    )


@router.get("/{file_id}", response_model=UploadResponse)
def get_file(file_id: str, db: Session = Depends(get_db)):
    row = db.get(UploadedFile, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")
    return _upload_response(row)


@router.get("/{file_id}/measurements/", response_model=MeasurementsResponse)
def get_measurements(
    file_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    row = db.get(UploadedFile, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")

    features = db.scalars(
        select(Feature)
        .where(Feature.file_id == file_id)
        .order_by(Feature.feature_index)
    ).all()

    total_area = 0.0
    total_length = 0.0
    unsupported = 0

    parsed = []
    for f in features:
        measurement = json.loads(f.measurement_json)
        if measurement.get("kind") == "area" and measurement.get("value") is not None:
            total_area += float(measurement["value"])
        elif measurement.get("kind") == "length" and measurement.get("value") is not None:
            total_length += float(measurement["value"])
        if not measurement.get("supported"):
            unsupported += 1

        parsed.append(
            FeatureResponse(
                feature_index=f.feature_index,
                feature_id=f.feature_id,
                geometry_type=f.geometry_type,
                geometry=json.loads(f.geometry_json),
                crs=row.crs,
                properties=json.loads(f.properties_json),
                measurement=Measurement(**measurement),
            )
        )

    return MeasurementsResponse(
        file_id=row.id,
        filename=row.filename,
        crs=row.crs,
        feature_count=row.feature_count,
        limit=limit,
        offset=offset,
        total_area_square_meters=total_area,
        total_length_meters=total_length,
        unsupported_count=unsupported,
        features=parsed[offset : offset + limit],
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: str, db: Session = Depends(get_db)):
    row = db.get(UploadedFile, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")

    storage_path = Path(row.storage_path)
    upload_dir = storage_path.parent

    db.delete(row)
    db.commit()

    import shutil
    shutil.rmtree(upload_dir, ignore_errors=True)
