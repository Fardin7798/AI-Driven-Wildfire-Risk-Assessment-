from datetime import date, datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import logger
from app.providers.base import RawDailyWeather, WeatherProvider


class NasaPowerWeatherProvider(WeatherProvider):
    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2.0, min=2, max=15),
        reraise=True,
    )
    async def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    async def fetch_weather_forecast(
        self, lat: float, lon: float, past_days: int = 3, forecast_days: int = 3
    ) -> list[RawDailyWeather]:
        # NASA POWER is a climatological / historical dataset, so it serves past days
        today = date.today()
        start = today.replace(day=max(1, today.day - past_days))
        return await self.fetch_historical_weather(lat, lon, start, today)

    async def fetch_historical_weather(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> list[RawDailyWeather]:
        params = {
            "parameters": "T2M_MAX,T2M_MIN,T2M,RH2M,WS10M,PRECTOTCORR",
            "community": "AG",
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON",
        }

        data = await self._get_json(params)
        properties = data.get("properties", {}).get("parameter", {})

        t_max_dict = properties.get("T2M_MAX", {})
        t_min_dict = properties.get("T2M_MIN", {})
        t_mean_dict = properties.get("T2M", {})
        rh_dict = properties.get("RH2M", {})
        wind_dict = properties.get("WS10M", {})
        precip_dict = properties.get("PRECTOTCORR", {})

        results: list[RawDailyWeather] = []
        for date_key, t_max in t_max_dict.items():
            try:
                rec_date = datetime.strptime(date_key, "%Y%m%d").date()
                results.append(
                    RawDailyWeather(
                        record_date=rec_date,
                        temp_max=float(t_max),
                        temp_min=float(t_min_dict.get(date_key, t_max - 5.0)),
                        temp_mean=float(t_mean_dict.get(date_key, t_max - 2.5)),
                        rh_mean=float(rh_dict.get(date_key, 50.0)),
                        rh_min=max(10.0, float(rh_dict.get(date_key, 50.0)) - 20.0),
                        wind_max=float(wind_dict.get(date_key, 10.0)) * 3.6,  # Convert m/s to km/h
                        precip_sum=float(precip_dict.get(date_key, 0.0)),
                        et0=3.5,  # Default estimation if not provided
                        soil_moisture=0.2,
                        provider="nasa_power",
                    )
                )
            except Exception as e:
                logger.warn("nasa_power_row_parse_error", date_key=date_key, error=str(e))
                continue

        return results
