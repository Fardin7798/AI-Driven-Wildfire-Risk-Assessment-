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
    """One day of weather. A value the source did not return stays None (never filled)."""

    record_date: date
    temp_max: float | None
    temp_min: float | None
    temp_mean: float | None
    rh_mean: float | None
    rh_min: float | None
    wind_max: float | None
    precip_sum: float | None
    et0: float | None
    soil_moisture: float | None
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
        self, bbox: Sequence[float], day_range: int = 1, start_date: date | None = None
    ) -> list[RawFireDetection]:
        """Fetch fire detections in bbox [west, south, east, north].

        Without start_date: the most recent day_range days. With start_date: day_range days
        starting at start_date (UTC).
        """
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
