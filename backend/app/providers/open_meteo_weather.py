from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import RawDailyWeather, WeatherProvider
from app.providers.open_meteo_http import get_json

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_min",
    "wind_speed_10m_max",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "soil_moisture_0_to_7cm_mean",
]


class OpenMeteoWeatherProvider(WeatherProvider):
    def __init__(
        self,
        forecast_url: str = settings.OPEN_METEO_WEATHER_URL,
        archive_url: str = settings.OPEN_METEO_ARCHIVE_URL,
    ):
        self.forecast_url = forecast_url
        self.archive_url = archive_url

    async def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        return await get_json(url, params)

    @staticmethod
    def _value(daily: dict[str, Any], key: str, i: int) -> float | None:
        """Return the i-th value of a daily series, or None when absent (never a default)."""
        series = daily.get(key)
        if not series or i >= len(series) or series[i] is None:
            return None
        return float(series[i])

    def _parse_daily_dict(
        self, daily: dict[str, Any], provider_name: str = "open_meteo"
    ) -> list[RawDailyWeather]:
        results: list[RawDailyWeather] = []
        for i, dt_str in enumerate(daily.get("time", [])):
            try:
                rec_date = datetime.strptime(dt_str, "%Y-%m-%d").date()
            except (TypeError, ValueError) as e:
                logger.warn("weather_parse_row_error", index=i, error=str(e))
                continue
            results.append(
                RawDailyWeather(
                    record_date=rec_date,
                    temp_max=self._value(daily, "temperature_2m_max", i),
                    temp_min=self._value(daily, "temperature_2m_min", i),
                    temp_mean=self._value(daily, "temperature_2m_mean", i),
                    rh_mean=self._value(daily, "relative_humidity_2m_mean", i),
                    rh_min=self._value(daily, "relative_humidity_2m_min", i),
                    wind_max=self._value(daily, "wind_speed_10m_max", i),
                    precip_sum=self._value(daily, "precipitation_sum", i),
                    et0=self._value(daily, "et0_fao_evapotranspiration", i),
                    soil_moisture=self._value(daily, "soil_moisture_0_to_7cm_mean", i),
                    provider=provider_name,
                )
            )
        return results

    async def fetch_weather_forecast_batch(
        self,
        coords: Sequence[tuple[float, float]],
        past_days: int = 3,
        forecast_days: int = 3,
    ) -> list[list[RawDailyWeather]]:
        """Fetch daily weather for many points in ONE request (Open-Meteo multi-location).

        Returns one list per input coordinate, in the same order.
        """
        if not coords:
            return []
        params = {
            "latitude": ",".join(f"{lat:.4f}" for lat, _ in coords),
            "longitude": ",".join(f"{lon:.4f}" for _, lon in coords),
            "daily": DAILY_VARIABLES,
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": "auto",
        }
        data = await self._get_json(self.forecast_url, params)
        payloads = data if isinstance(data, list) else [data]
        if len(payloads) != len(coords):
            raise ValueError(
                f"Open-Meteo returned {len(payloads)} locations for {len(coords)} requested"
            )
        return [self._parse_daily_dict(p.get("daily", {})) for p in payloads]

    async def fetch_weather_forecast(
        self, lat: float, lon: float, past_days: int = 3, forecast_days: int = 3
    ) -> list[RawDailyWeather]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": DAILY_VARIABLES,
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": "auto",
        }
        data = await self._get_json(self.forecast_url, params)
        daily = data.get("daily", {})
        return self._parse_daily_dict(daily, provider_name="open_meteo")

    async def fetch_historical_weather(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> list[RawDailyWeather]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": DAILY_VARIABLES,
            "timezone": "auto",
        }
        data = await self._get_json(self.archive_url, params)
        daily = data.get("daily", {})
        return self._parse_daily_dict(daily, provider_name="open_meteo_archive")
