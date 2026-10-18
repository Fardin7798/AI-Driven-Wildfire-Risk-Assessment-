from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    APP_VERSION: str = "2.0.0"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/postgres"

    ALLOWED_ORIGINS: str | list[str] = ["*"]

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        return [str(self.ALLOWED_ORIGINS)]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    JOB_TOKEN: str = "dev-job-token"

    FIRMS_MAP_KEY: str = ""
    FIRMS_SOURCES: str | list[str] = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "MODIS_NRT"]

    @field_validator("FIRMS_SOURCES", mode="before")
    @classmethod
    def parse_firms_sources(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    DATAGOVIN_API_KEY: str = ""
    ENABLE_CPCB: bool = False
    ENABLE_SCHEDULER: bool = True

    DEFAULT_COUNTRY: str = "IN"

    MODEL_DIR: str = str(Path(__file__).resolve().parents[2] / "models")
    ACTIVE_WILDFIRE_MODEL: str = "wildfire_xgb_v1"
    ACTIVE_AQI_MODEL: str = "aqi_prophet_v1"

    OPEN_METEO_WEATHER_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"

    RETENTION_DAYS: int = 400


settings = Settings()
