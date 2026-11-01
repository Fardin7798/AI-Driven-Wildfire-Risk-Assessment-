from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.domain.aqi import calculate_cpcb_aqi
from app.providers.base import AirQualityProvider, RawAQObservation
from app.providers.open_meteo_http import get_json

POLLUTANTS = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
]


class OpenMeteoAirProvider(AirQualityProvider):
    def __init__(self, air_url: str = settings.OPEN_METEO_AIR_QUALITY_URL):
        self.air_url = air_url

    async def _get_json(self, params: dict[str, Any]) -> Any:
        return await get_json(self.air_url, params)

    async def fetch_air_quality(self, lat: float, lon: float) -> list[RawAQObservation]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": POLLUTANTS,
            "timezone": "UTC",
        }
        data = await self._get_json(params)
        return self._parse_current(data, lat, lon)

    def _parse_current(
        self, data: dict[str, Any], lat: float, lon: float
    ) -> list[RawAQObservation]:
        results: list[RawAQObservation] = []
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

    async def fetch_air_quality_batch(
        self, coords: Sequence[tuple[float, float]]
    ) -> list[list[RawAQObservation]]:
        """Current CAMS pollutant values for many points in ONE request (multi-location)."""
        if not coords:
            return []
        params = {
            "latitude": ",".join(f"{lat:.4f}" for lat, _ in coords),
            "longitude": ",".join(f"{lon:.4f}" for _, lon in coords),
            "current": POLLUTANTS,
            "timezone": "UTC",
        }
        data = await self._get_json(params)
        payloads = data if isinstance(data, list) else [data]
        if len(payloads) != len(coords):
            raise ValueError(
                f"Open-Meteo AQ returned {len(payloads)} locations for {len(coords)} requested"
            )
        return [
            self._parse_current(p, lat, lon) for p, (lat, lon) in zip(payloads, coords, strict=True)
        ]
