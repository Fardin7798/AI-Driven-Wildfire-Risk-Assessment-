from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class RawFireDetection:
    lat: float
    lon: float
    brightness: float | None
    frp: float | None
    confidence: str
    acq_datetime_utc: datetime
    satellite: str
    instrument: str
    daynight: str
    source: str


@dataclass(frozen=True)
class RawDailyWeather:
    record_date: date
    temp_max: float
    temp_min: float
    temp_mean: float
    rh_mean: float
    rh_min: float
    wind_max: float
    precip_sum: float
    et0: float
    soil_moisture: float
    provider: str


@dataclass(frozen=True)
class RawAQObservation:
    observed_at_utc: datetime
    pm25: float | None
    pm10: float | None
    no2: float | None
    so2: float | None
    co: float | None
    o3: float | None
    nh3: float | None
    aqi: int | None
    aqi_category: str | None
    provider: str
    station_external_id: str | None = None
    station_name: str | None = None
    city: str | None = None
    state: str | None = None
    lat: float | None = None
    lon: float | None = None


class FireProvider(Protocol):
    async def fetch_live_fires(
        self, bbox: Sequence[float], day_range: int = 1
    ) -> list[RawFireDetection]:
        """Fetch active fire thermal detections within bounding box [west, south, east, north]."""
        ...


class WeatherProvider(Protocol):
    async def fetch_weather_forecast(
        self, lat: float, lon: float, past_days: int = 3, forecast_days: int = 3
    ) -> list[RawDailyWeather]:
        """Fetch weather observations and synoptic forecast."""
        ...

    async def fetch_historical_weather(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> list[RawDailyWeather]:
        """Fetch historical daily weather archive."""
        ...


class AirQualityProvider(Protocol):
    async def fetch_air_quality(self, lat: float, lon: float) -> list[RawAQObservation]:
        """Fetch current air quality observations and trajectory."""
        ...
