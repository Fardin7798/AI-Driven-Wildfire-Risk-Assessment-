"""Current district AQI from Open-Meteo air quality (Copernicus CAMS), CPCB-averaged.

The request asks for the hourly values of the trailing 24-h window ending at the latest whole UTC
hour; `app.domain.aqi_features.current_concentrations` applies the CPCB averaging (24-h means,
max 8-h running mean for CO/O3) and `app.domain.aqi.calculate_cpcb_aqi` the CPCB AQI rule.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from app.core.config import settings
from app.core.logging import logger
from app.domain.aqi import calculate_cpcb_aqi
from app.domain.aqi_features import (
    CAMS_AVERAGED_PROVIDER,
    POLLUTANTS,
    clean_hourly,
    current_concentrations,
    current_window_end,
    current_window_start,
)
from app.providers.base import AirQualityProvider, RawAQObservation
from app.providers.open_meteo_http import get_json


def window_params(end: datetime) -> dict[str, Any]:
    """Hourly CAMS pollutants for the 24 hours ending at `end` (naive UTC), in UTC."""
    return {
        "hourly": ",".join(POLLUTANTS),
        "timezone": "UTC",
        "start_hour": current_window_start(end).strftime("%Y-%m-%dT%H:%M"),
        "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
    }


def parse_window(data: dict[str, Any], lat: float, lon: float, end: datetime) -> RawAQObservation:
    """Open-Meteo payload for one location -> one CPCB-averaged observation at `end`.

    Raises ValueError when the payload has no hourly block.
    """
    hourly = data.get("hourly")
    if not hourly or not hourly.get("time"):
        raise ValueError("Open-Meteo AQ payload has no hourly values")
    conc = current_concentrations(clean_hourly(pd.DataFrame(hourly)), end)
    # CO from Open-Meteo is in µg/m³; the CPCB CO breakpoints are in mg/m³.
    co_mg = conc["co"] / 1000.0 if conc["co"] is not None else None
    aqi = calculate_cpcb_aqi({**conc, "co": co_mg})
    return RawAQObservation(
        observed_at_utc=end.replace(tzinfo=UTC),
        pm25=conc["pm25"],
        pm10=conc["pm10"],
        no2=conc["no2"],
        so2=conc["so2"],
        co=co_mg,
        o3=conc["o3"],
        nh3=None,
        aqi=aqi.aqi if aqi else None,
        aqi_category=aqi.category if aqi else None,
        provider=CAMS_AVERAGED_PROVIDER,
        lat=lat,
        lon=lon,
    )


class OpenMeteoAirProvider(AirQualityProvider):
    def __init__(self, air_url: str = settings.OPEN_METEO_AIR_QUALITY_URL):
        self.air_url = air_url

    async def fetch_air_quality(
        self, lat: float, lon: float, now: datetime | None = None
    ) -> list[RawAQObservation]:
        return (await self.fetch_air_quality_batch([(lat, lon)], now=now))[0]

    async def fetch_air_quality_batch(
        self, coords: Sequence[tuple[float, float]], now: datetime | None = None
    ) -> list[list[RawAQObservation]]:
        """CPCB-averaged current values for many points in ONE request (multi-location).

        A location whose payload cannot be parsed gets an empty list (logged), never a filled one.
        """
        if not coords:
            return []
        end = current_window_end(now or datetime.now(UTC))
        params = {
            "latitude": ",".join(f"{lat:.4f}" for lat, _ in coords),
            "longitude": ",".join(f"{lon:.4f}" for _, lon in coords),
            **window_params(end),
        }
        data = await get_json(self.air_url, params)
        payloads = data if isinstance(data, list) else [data]
        if len(payloads) != len(coords):
            raise ValueError(
                f"Open-Meteo AQ returned {len(payloads)} locations for {len(coords)} requested"
            )
        out: list[list[RawAQObservation]] = []
        for payload, (lat, lon) in zip(payloads, coords, strict=True):
            try:
                out.append([parse_window(payload, lat, lon, end)])
            except (ValueError, KeyError) as e:
                logger.warn("aqi_window_parse_error", lat=lat, lon=lon, error=str(e))
                out.append([])
        return out
