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

            stations_map: dict[str, dict[str, Any]] = {}
            for rec in records:
                s_name = rec.get("station") or rec.get("id") or "unknown"
                if s_name not in stations_map:
                    lat_str = rec.get("latitude")
                    lon_str = rec.get("longitude")
                    stations_map[s_name] = {
                        "city": rec.get("city", ""),
                        "state": rec.get("state", ""),
                        "station_name": s_name,
                        "station_external_id": str(rec.get("id", s_name)),
                        "lat": float(lat_str) if lat_str else None,
                        "lon": float(lon_str) if lon_str else None,
                        "pollutants": {
                            "pm25": None,
                            "pm10": None,
                            "no2": None,
                            "so2": None,
                            "co": None,
                            "o3": None,
                            "nh3": None,
                        },
                    }

                p_id = (rec.get("pollutant_id") or "").upper().replace(".", "")
                p_avg = rec.get("pollutant_avg")
                if p_avg is not None:
                    try:
                        p_val = float(p_avg)
                        p_key_map = {
                            "PM25": "pm25",
                            "PM10": "pm10",
                            "NO2": "no2",
                            "SO2": "so2",
                            "CO": "co",
                            "OZONE": "o3",
                            "O3": "o3",
                            "NH3": "nh3",
                        }
                        if p_id in p_key_map:
                            stations_map[s_name]["pollutants"][p_key_map[p_id]] = p_val
                    except (ValueError, TypeError):
                        pass

            for s_info in stations_map.values():
                try:
                    aqi_calc = calculate_cpcb_aqi(s_info["pollutants"])
                    results.append(
                        RawAQObservation(
                            observed_at_utc=now_utc,
                            pm25=s_info["pollutants"]["pm25"],
                            pm10=s_info["pollutants"]["pm10"],
                            no2=s_info["pollutants"]["no2"],
                            so2=s_info["pollutants"]["so2"],
                            co=s_info["pollutants"]["co"],
                            o3=s_info["pollutants"]["o3"],
                            nh3=s_info["pollutants"]["nh3"],
                            aqi=aqi_calc.aqi if aqi_calc else None,
                            aqi_category=aqi_calc.category if aqi_calc else None,
                            provider="cpcb_datagovin",
                            station_external_id=s_info["station_external_id"],
                            station_name=s_info["station_name"],
                            city=s_info["city"],
                            state=s_info["state"],
                            lat=s_info["lat"],
                            lon=s_info["lon"],
                        )
                    )
                except Exception as row_err:
                    logger.warn("cpcb_station_parse_error", error=str(row_err))
                    continue

        except Exception as e:
            logger.error("cpcb_datagovin_fetch_failed", error=str(e))

        return results
