from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.domain.aqi import calculate_cpcb_aqi
from app.providers.base import RawAQObservation


class CPCBDataGovInProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.DATAGOVIN_API_KEY
        self.enabled = settings.ENABLE_CPCB and bool(self.api_key)
        self.resource_url = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"

    async def fetch_station_observations(self, limit: int = 500) -> list[RawAQObservation]:
        """Fetch real-time hourly snapshot from CPCB national CAAQMS network on data.gov.in."""
        if not self.enabled:
            logger.info("cpcb_datagovin_disabled_or_no_key")
            return []

        params = {
            "api-key": str(self.api_key),
            "format": "json",
            "limit": str(limit),
        }

        results: list[RawAQObservation] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
                resp = await client.get(self.resource_url, params=params)
                resp.raise_for_status()
                payload = resp.json()

            records: list[dict[str, Any]] = payload.get("records", [])
            now_utc = datetime.now(UTC)

            for rec in records:
                try:
                    city = rec.get("city", "")
                    state = rec.get("state", "")
                    station = rec.get("station", "")
                    lat_str = rec.get("latitude")
                    lon_str = rec.get("longitude")
                    lat = float(lat_str) if lat_str else None
                    lon = float(lon_str) if lon_str else None

                    # Extract pollutants
                    pollutants = {
                        "pm25": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "PM2.5" and rec.get("pollutant_avg")
                        else None,
                        "pm10": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "PM10" and rec.get("pollutant_avg")
                        else None,
                        "no2": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "NO2" and rec.get("pollutant_avg")
                        else None,
                        "so2": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "SO2" and rec.get("pollutant_avg")
                        else None,
                        "co": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "CO" and rec.get("pollutant_avg")
                        else None,
                        "o3": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "OZONE" and rec.get("pollutant_avg")
                        else None,
                        "nh3": float(rec["pollutant_avg"])
                        if rec.get("pollutant_id") == "NH3" and rec.get("pollutant_avg")
                        else None,
                    }

                    aqi_calc = calculate_cpcb_aqi(pollutants)

                    results.append(
                        RawAQObservation(
                            observed_at_utc=now_utc,
                            pm25=pollutants["pm25"],
                            pm10=pollutants["pm10"],
                            no2=pollutants["no2"],
                            so2=pollutants["so2"],
                            co=pollutants["co"],
                            o3=pollutants["o3"],
                            nh3=pollutants["nh3"],
                            aqi=aqi_calc.aqi if aqi_calc.aqi > 0 else None,
                            aqi_category=aqi_calc.category if aqi_calc.aqi > 0 else None,
                            provider="cpcb_datagovin",
                            station_external_id=rec.get("id", station),
                            station_name=station,
                            city=city,
                            state=state,
                            lat=lat,
                            lon=lon,
                        )
                    )
                except Exception as row_err:
                    logger.warn("cpcb_row_parse_error", error=str(row_err))
                    continue

        except Exception as e:
            logger.error("cpcb_datagovin_fetch_failed", error=str(e))

        return results
