from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger
from app.domain.aqi import calculate_cpcb_aqi
from app.providers.base import AirQualityProvider, RawAQObservation


class OpenMeteoAirProvider(AirQualityProvider):
    def __init__(self, air_url: str = settings.OPEN_METEO_AIR_QUALITY_URL):
        self.air_url = air_url

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2.0, min=2, max=15),
        reraise=True,
    )
    async def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.air_url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def fetch_air_quality(self, lat: float, lon: float) -> list[RawAQObservation]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": [
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
            ],
            "hourly": [
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
            ],
            "forecast_days": 3,
            "timezone": "UTC",
        }
        data = await self._get_json(params)
        results: list[RawAQObservation] = []

        # 1. Parse Current Observation
        current = data.get("current", {})
        if current:
            try:
                dt_str = current.get("time", "")
                dt = datetime.fromisoformat(dt_str).replace(tzinfo=UTC)
                pm25 = current.get("pm2_5")
                pm10 = current.get("pm10")
                no2 = current.get("nitrogen_dioxide")
                so2 = current.get("sulphur_dioxide")
                co = current.get("carbon_monoxide")
                # CO from Open-Meteo is in µg/m³; convert to mg/m³ for Indian CPCB standard
                co_mg = (co / 1000.0) if co is not None else None
                o3 = current.get("ozone")

                aqi_calc = calculate_cpcb_aqi(
                    {
                        "pm25": pm25,
                        "pm10": pm10,
                        "no2": no2,
                        "so2": so2,
                        "co": co_mg,
                        "o3": o3,
                    }
                )

                results.append(
                    RawAQObservation(
                        observed_at_utc=dt,
                        pm25=pm25,
                        pm10=pm10,
                        no2=no2,
                        so2=so2,
                        co=co_mg,
                        o3=o3,
                        nh3=None,
                        aqi=aqi_calc.aqi,
                        aqi_category=aqi_calc.category,
                        provider="copernicus_cams",
                        lat=lat,
                        lon=lon,
                    )
                )
            except Exception as e:
                logger.warn("aqi_current_parse_error", error=str(e))

        return results
