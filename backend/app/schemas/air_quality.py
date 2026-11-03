from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.names import ReadableName


class AQObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int | None = None
    district_name: ReadableName | None = None
    state_name: ReadableName | None = None
    observed_at_utc: datetime
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    so2: float | None = None
    co: float | None = None
    o3: float | None = None
    nh3: float | None = None
    aqi: int | None = None
    aqi_category: str | None = None
    provider: str
    as_of: dict[str, str]
    disclaimer_short: str


class AQIForecastPoint(BaseModel):
    horizon: int
    target_date: date
    pm25_si_pred: float
    category: str


class DistrictAQIForecast(BaseModel):
    """Model-B forecast of one district for its latest origin day, or why it was skipped."""

    region_id: int
    district_name: ReadableName | None = None
    state_name: ReadableName | None = None
    status: Literal["forecast", "skipped"]
    origin_date: date
    model_version: str
    source: str | None = None
    extrapolated: bool | None = None
    forecasts: list[AQIForecastPoint] = Field(default_factory=list)
    skip_reason: str | None = None


class RegionAQIForecastResponse(DistrictAQIForecast):
    as_of: dict[str, str]
    disclaimer_short: str


class AQIForecastCounts(BaseModel):
    forecast: int
    skipped: int


class AllAQIForecastsResponse(BaseModel):
    model_version: str
    counts: AQIForecastCounts
    districts: list[DistrictAQIForecast]
    as_of: dict[str, str]
    disclaimer_short: str
