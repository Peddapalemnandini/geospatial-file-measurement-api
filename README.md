# Geospatial File Measurement API

A production-style FastAPI backend for the Aereo Software Development Intern assignment.

## What it does

- Uploads `.kml`, `.kmz`, or zipped ESRI Shapefile files.
- Reads every feature and returns geometry, attributes and CRS.
- Calculates polygon area in **square metres**.
- Calculates line length in **metres**.
- Uses CRS-aware local projections instead of treating longitude/latitude degrees as distances.
- Stores uploads and processed features in SQLite.
- Provides pagination, deletion and a health endpoint.
- Includes automated tests and a Dockerfile.

> The implementation is intentionally original. It is designed around the assignment's core problem rather than copying another candidate's solution.

## Architecture

```text
Client
  |
  v
FastAPI
  |
  +--> upload validation
  |
  +--> KML parser / Shapefile reader
  |
  +--> CRS-aware measurement service
  |
  +--> SQLite persistence
  |
  v
JSON response
```

## Supported geometry

| Geometry | Measurement |
|---|---|
| Polygon | Area in m² |
| MultiPolygon | Area in m² |
| LineString | Length in m |
| MultiLineString | Length in m |
| Point / MultiPoint | No area/length |
| GeometryCollection | Reported as unsupported |

## Why CRS handling matters

A KML normally uses WGS84 longitude/latitude. Those coordinates are angular degrees, not metres. The service therefore transforms geographic data into a local projected CRS before calculating area or length.

For polygons, a local Lambert azimuthal equal-area projection is used. For lines, a local azimuthal-equidistant projection is used. Existing projected CRSs with linear units are used directly, except Web Mercator, which is reprojected before measurement.

GeoPandas provides the file-reading layer for spatial files, while FastAPI's `UploadFile` is used for multipart uploads.

## Local setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## API

### 1. Upload

```http
POST /api/files/
```

Multipart field:

```text
file
```

Example:

```bash
curl -X POST \
  -F "file=@samples/sample.kml" \
  http://127.0.0.1:8000/api/files/
```

Example response:

```json
{
  "id": "generated-uuid",
  "filename": "sample.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "file_type": "kml",
  "created_at": "2026-10-08T00:00:00Z"
}
```

### 2. Measurements

```http
GET /api/files/{file_id}/measurements/
```

Optional:

```text
limit=100
offset=0
```

The response contains:

- total polygon area
- total line length
- feature count
- unsupported feature count
- per-feature geometry
- per-feature properties
- per-feature measurement
- measurement CRS

### 3. File metadata

```http
GET /api/files/{file_id}
```

### 4. List files

```http
GET /api/files/?limit=50&offset=0
```

### 5. Delete

```http
DELETE /api/files/{file_id}
```

### 6. Health

```http
GET /health
```

## Error handling

- `400` - empty file, unsupported extension, malformed/unsafe archive
- `413` - upload/archive/feature limit exceeded
- `422` - valid extension but unreadable geospatial contents
- `404` - unknown file id

## Security considerations

The upload pipeline:

1. strips path components from filenames
2. limits upload size
3. validates extensions
4. checks ZIP member count
5. checks uncompressed archive size
6. rejects ZIP path traversal
7. requires the standard Shapefile companion files
8. never trusts a missing `.prj` by guessing a CRS

## Testing

```bash
pytest -q
```

## Docker

```bash
docker build -t geospatial-file-measurement-api .
docker run --rm -p 8000:8000 geospatial-file-measurement-api
```

Then open `http://127.0.0.1:8000/docs`.

## Suggested demo

Use `samples/sample.kml`.

1. Start the API.
2. Open `/docs`.
3. Open `POST /api/files/`.
4. Upload `samples/sample.kml`.
5. Copy the returned `id`.
6. Call `GET /api/files/{id}/measurements/`.
7. Show the area/length results and explain why the API does not calculate directly in degrees.

## Future improvements

- PostgreSQL/PostGIS for production scale
- Redis/background jobs for large uploads
- authentication and per-user quotas
- object storage
- GeoJSON/GeoPackage support
- geodesic measurement as an optional comparison
- CI/CD and deployment to a cloud platform
