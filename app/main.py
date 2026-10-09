from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.config import settings
from app.database import Base, engine

# Create required directories
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path("./data").mkdir(parents=True, exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Upload geospatial files and calculate polygon area and line length "
        "in metres using CRS-aware projections."
    ),
)

# Register API routes
app.include_router(router)


# Homepage / dashboard
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    html_file = Path(__file__).parent / "static" / "index.html"

    if html_file.exists():
        return html_file.read_text(encoding="utf-8")

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GeoMeasure Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #0b1020;
                color: #eef4ff;
                padding: 50px;
            }
            .card {
                max-width: 650px;
                margin: 40px auto;
                padding: 30px;
                background: #151f35;
                border: 1px solid #263550;
                border-radius: 16px;
            }
            a {
                display: inline-block;
                margin-top: 15px;
                padding: 12px 18px;
                background: #7667f5;
                color: white;
                text-decoration: none;
                border-radius: 8px;
            }
            .status { color: #57e0a3; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>GeoMeasure</h1>
            <p class="status">● API is running</p>
            <p>Geospatial File Measurement API</p>
            <p>
                The dashboard HTML file is missing.
                Create app/static/index.html to display the full interface.
            </p>
            <a href="/docs">Open API Documentation</a>
        </div>
    </body>
    </html>
    """


# Health check
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}