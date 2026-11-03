"""NASA POWER daily point weather (fallback provider; the live path uses Open-Meteo).

Variables and units match ml/pipeline/download_power_history.py (the wildfire training archive):

    T2M_MAX      -> temp_max   (deg C)
    T2M_MIN      -> temp_min   (deg C)
    T2M          -> temp_mean  (deg C)
    RH2M         -> rh_mean    (%)
    WS10M_MAX    -> wind_max   (m/s -> km/h, Open-Meteo unit)
    PRECTOTCORR  -> precip_sum (mm/day)

POWER marks a value it does not have with a fill value (-999, also given in the response
header). Such values, and dates a parameter does not return, are stored as None, exactly like
training keeps them as NaN (values <= -998). Nothing is filled: POWER has no daily RH minimum,
FAO ET0 or volumetric soil moisture, so rh_min, et0 and soil_moisture are always None.
"""

from datetime import date, datetime, timedelta
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import logger
from app.core.timeutil import today_ist
from app.providers.base import RawDailyWeather, WeatherProvider

PARAMETERS = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS10M_MAX", "PRECTOTCORR"]
# Same rule as training (download_power_history.to_frame): anything <= -998 is the fill value.
FILL_THRESHOLD = -998.0
MS_TO_KMH = 3.6


def _value(series: dict[str, Any], date_key: str, fill_value: float) -> float | None:
    """One day of one parameter, or None when absent or the POWER fill value."""
    raw = series.get(date_key)
    if raw is None:
        return None
    v = float(raw)
    if v != v or v == fill_value or v <= FILL_THRESHOLD:  # NaN or fill
        return None
    return v


def parse_power_daily(data: dict[str, Any]) -> list[RawDailyWeather]:
    """Parse a POWER daily point JSON response; missing values stay None."""
    params: dict[str, dict[str, Any]] = data.get("properties", {}).get("parameter", {})
    fill_value = float(data.get("header", {}).get("fill_value", -999.0))
    date_keys = sorted({k for p in PARAMETERS for k in params.get(p, {})})

    results: list[RawDailyWeather] = []
    for date_key in date_keys:
        try:
            rec_date = datetime.strptime(date_key, "%Y%m%d").date()
        except ValueError as e:
            logger.warn("nasa_power_row_parse_error", date_key=date_key, error=str(e))
            continue
        v = {p: _value(params.get(p, {}), date_key, fill_value) for p in PARAMETERS}
        wind_ms = v["WS10M_MAX"]
        results.append(
            RawDailyWeather(
                record_date=rec_date,
                temp_max=v["T2M_MAX"],
                temp_min=v["T2M_MIN"],
                temp_mean=v["T2M"],
                rh_mean=v["RH2M"],
                rh_min=None,
                wind_max=wind_ms * MS_TO_KMH if wind_ms is not None else None,
                precip_sum=v["PRECTOTCORR"],
                et0=None,
                soil_moisture=None,
                provider="nasa_power",
            )
        )

    missing = [
        r.record_date.isoformat()
        for r in results
        if None in (r.temp_max, r.temp_mean, r.rh_mean, r.wind_max, r.precip_sum)
    ]
    if missing:
        logger.warn("nasa_power_days_with_missing_values", count=len(missing), dates=missing)
    return results


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
        # NASA POWER is an archive: it serves past days only (no forecast_days).
        today = today_ist()
        return await self.fetch_historical_weather(
            lat, lon, today - timedelta(days=past_days), today
        )

    async def fetch_historical_weather(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> list[RawDailyWeather]:
        params = {
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON",
        }
        return parse_power_daily(await self._get_json(params))
