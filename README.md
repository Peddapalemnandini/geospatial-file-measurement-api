
# Geospatial File Measurement API

A FastAPI-based backend project for the Aereo Software Development Intern assignment. It processes geospatial files and calculates polygon areas and line lengths using CRS-aware projections.

## Features

- Upload KML, KMZ, and zipped ESRI Shapefile files
- Extract geometry, attributes, and coordinate reference system (CRS)
- Calculate polygon area in square metres
- Calculate line length in metres
- Transform geographic coordinates before measurement
- Store uploaded files and processed features in SQLite
- Support pagination, file deletion, and health checks
- Include automated tests and Docker support

## Technology Stack

- Python
- FastAPI
- GeoPandas
- Shapely
- SQLAlchemy
- SQLite
- Pytest
- Docker

## Architecture

```text
Client
  |
FastAPI
  |
Upload Validation
  |
Geospatial File Processing
  |
CRS-Aware Measurement
  |
SQLite Database
  |
JSON Response
```

## Supported Geometry

| Geometry | Measurement |
|---|---|
| Polygon | Area in m² |
| MultiPolygon | Area in m² |
| LineString | Length in m |
| MultiLineString | Length in m |
| Point / MultiPoint | No area or length |
| GeometryCollection | Unsupported |

## Why CRS Handling Matters

Longitude and latitude coordinates use angular degrees, not metres. The application transforms geographic data into an appropriate local projected coordinate reference system before calculating area or length.

GeoPandas handles geospatial file reading, while FastAPI provides the REST API.

## Installation and Setup

### Windows

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

Open these URLs after starting the application:

- **API Documentation:** http://127.0.0.1:8000/docs
- **Health Check:** http://127.0.0.1:8000/health
- **Dashboard:** http://127.0.0.1:8000/

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/files/` | Upload a geospatial file |
| GET | `/api/files/` | List uploaded files |
| GET | `/api/files/{file_id}` | Retrieve file metadata |
| GET | `/api/files/{file_id}/measurements/` | Retrieve measurements |
| DELETE | `/api/files/{file_id}` | Delete a file |
| GET | `/health` | Check API status |

## Screenshots

Add your actual screenshots to the `screenshots/` folder in the project.

### Dashboard
<img width="1917" height="1026" alt="image" src="https://github.com/user-attachments/assets/2d1284e9-a805-4dff-8a67-9ae0e33a130d" />




### API Documentation

<img width="1902" height="907" alt="image" src="https://github.com/user-attachments/assets/c4b1645a-e590-4498-a077-d6d246966113" />


### File Upload Result
<img width="1903" height="1023" alt="image" src="https://github.com/user-attachments/assets/6a76d415-84ae-4c63-9c86-30a828e78c78" />



### Measurement Results
<img width="1898" height="1008" alt="image" src="https://github.com/user-attachments/assets/6931ac3e-7900-4650-9c9c-15aa23b36853" />

### api

<img width="1903" height="1023" alt="image" src="https://github.com/user-attachments/assets/4c37126f-4101-4f2c-8a1e-500517923599" />



> Ensure the image filenames match the files in your screenshots folder exactly.

## Testing

Run the automated tests using:

```bash
pytest -q
```

## Docker

Build the Docker image:

```bash
docker build -t geospatial-file-measurement-api .
```

Run the application:

```bash
docker run --rm -p 8000:8000 geospatial-file-measurement-api
```

Then open http://127.0.0.1:8000/docs.

## Security

The upload pipeline is designed to validate filenames and extensions, limit upload and archive sizes, check ZIP contents, reject path traversal, and require standard Shapefile companion files.

## Future Improvements

- PostgreSQL/PostGIS support
- Background processing for large uploads
- Authentication and user quotas
- Cloud object storage
- Additional geospatial formats
- CI/CD and cloud deployment

## Author

Developed as a geospatial file measurement project using Python and FastAPI.
