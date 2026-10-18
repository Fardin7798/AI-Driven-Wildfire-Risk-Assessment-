from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AQObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int | None = None
    district_name: str | None = None
    state_name: str | None = None
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


class AQForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int
    district_name: str | None = None
    target_date: date
    horizon_days: int
    pm25_pred: float
    aqi_pred: int
    aqi_category: str
    model_version: str
    as_of: dict[str, str]
    disclaimer_short: str
