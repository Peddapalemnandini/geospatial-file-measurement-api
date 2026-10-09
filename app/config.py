from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Geospatial File Measurement API"
    database_url: str = "sqlite:///./data/measurements.db"
    upload_dir: str = "./data/uploads"
    max_upload_bytes: int = 50 * 1024 * 1024
    max_unzipped_bytes: int = 200 * 1024 * 1024
    max_zip_files: int = 100
    max_features: int = 50_000

    model_config = SettingsConfigDict(env_prefix="GEO_", env_file=".env")


settings = Settings()
