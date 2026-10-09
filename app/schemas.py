from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str
    filename: str
    feature_count: int
    crs: str | None
    status: str
    file_type: str
    created_at: datetime


class Measurement(BaseModel):
    supported: bool
    kind: str | None = None
    value: float | None = None
    unit: str | None = None
    measurement_crs: str | None = None
    note: str | None = None


class FeatureResponse(BaseModel):
    feature_index: int
    feature_id: str
    geometry_type: str
    geometry: dict[str, Any]
    crs: str | None
    properties: dict[str, Any]
    measurement: Measurement


class MeasurementsResponse(BaseModel):
    file_id: str
    filename: str
    crs: str | None
    feature_count: int
    limit: int
    offset: int
    total_area_square_meters: float
    total_length_meters: float
    unsupported_count: int
    features: list[FeatureResponse]


class FileListResponse(BaseModel):
    items: list[UploadResponse]
    limit: int
    offset: int
