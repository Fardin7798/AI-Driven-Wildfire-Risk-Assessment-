from datetime import date, datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import RawDailyWeather, WeatherProvider


class OpenMeteoWeatherProvider(WeatherProvider):
    def __init__(
        self,
        forecast_url: str = settings.OPEN_METEO_WEATHER_URL,
        archive_url: str = settings.OPEN_METEO_ARCHIVE_URL,
    ):
        self.forecast_url = forecast_url
        self.archive_url = archive_url

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2.0, min=2, max=15),
        reraise=True,
    )
    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                logger.warn("open_meteo_rate_limited", url=url)
            resp.raise_for_status()
            return resp.json()

    def _parse_daily_dict(
        self, daily: dict[str, Any], provider_name: str = "open_meteo"
    ) -> list[RawDailyWeather]:
        results: list[RawDailyWeather] = []
        time_list = daily.get("time", [])

        for i, dt_str in enumerate(time_list):
            try:
                rec_date = datetime.strptime(dt_str, "%Y-%m-%d").date()
                results.append(
                    RawDailyWeather(
                        record_date=rec_date,
                        temp_max=float(daily.get("temperature_2m_max", [0.0])[i] or 0.0),
                        temp_min=float(daily.get("temperature_2m_min", [0.0])[i] or 0.0),
                        temp_mean=float(daily.get("temperature_2m_mean", [0.0])[i] or 0.0),
                        rh_mean=float(daily.get("relative_humidity_2m_mean", [50.0])[i] or 50.0),
                        rh_min=float(daily.get("relative_humidity_2m_min", [30.0])[i] or 30.0),
                        wind_max=float(daily.get("wind_speed_10m_max", [10.0])[i] or 10.0),
                        precip_sum=float(daily.get("precipitation_sum", [0.0])[i] or 0.0),
                        et0=float(daily.get("et0_fao_evapotranspiration", [3.0])[i] or 3.0),
                        soil_moisture=float(
                            daily.get("soil_moisture_0_to_7cm_mean", [0.2])[i] or 0.2
                        ),
                        provider=provider_name,
                    )
                )
            except Exception as e:
                logger.warn("weather_parse_row_error", index=i, error=str(e))
                continue

        return results

    async def fetch_weather_forecast(
        self, lat: float, lon: float, past_days: int = 3, forecast_days: int = 3
    ) -> list[RawDailyWeather]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "relative_humidity_2m_mean",
                "relative_humidity_2m_min",
                "wind_speed_10m_max",
                "precipitation_sum",
                "et0_fao_evapotranspiration",
                "soil_moisture_0_to_7cm_mean",
            ],
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
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "relative_humidity_2m_mean",
                "relative_humidity_2m_min",
                "wind_speed_10m_max",
                "precipitation_sum",
                "et0_fao_evapotranspiration",
                "soil_moisture_0_to_7cm_mean",
            ],
            "timezone": "auto",
        }
        data = await self._get_json(self.archive_url, params)
        daily = data.get("daily", {})
        return self._parse_daily_dict(daily, provider_name="open_meteo_archive")
