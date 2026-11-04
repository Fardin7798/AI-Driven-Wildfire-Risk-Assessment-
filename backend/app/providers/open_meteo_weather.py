"""Open-Meteo weather for wildfire_xgb_v3: ECMWF IFS HRES 9 km (`models=ecmwf_ifs`) only.

Training (ml/pipeline/prepare_ifs_weather.py + work IFS extraction) used ECMWF IFS HRES with the
Open-Meteo day boundary for `timezone=Asia/Kolkata`: Open-Meteo truncates the +05:30 offset to
5 h, so local day D = hourly steps D-1 19:00 UTC .. D 18:00 UTC (24 steps). In the response the
hourly `time` strings of that day all start with "D" (D T00:00 .. D T23:00), so grouping hourly
values by the date prefix of `time` gives exactly the training day.

Per day:
  temp_max / temp_min = max / min of the 24 HOURLY temperature_2m values of that day. A day with
                        fewer than 24 hourly values or any null hour -> None (counted, logged).
                        The API's native daily temperature_2m_max/min are NOT used: for IFS they
                        come from ECMWF's own 3/6-hourly max/min fields and differed from the
                        hourly-derived training values by up to 0.65 / 0.83 C (live check
                        2026-11-03).
  temp_mean, rh_mean, rh_min, wind_max, precip_sum, et0, soil_moisture = API daily aggregates
                        (equal to the training aggregates within API rounding).
Nothing is ever filled: a value the API does not return stays None.
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import RawDailyWeather, WeatherProvider
from app.providers.open_meteo_http import get_json

WEATHER_MODEL = "ecmwf_ifs"
# Fixed (not "auto") so every district gets the training day boundary (19:00 UTC).
TIMEZONE = "Asia/Kolkata"
HOURS_PER_DAY = 24

DAILY_VARIABLES = [
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_min",
    "wind_speed_10m_max",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "soil_moisture_0_to_7cm_mean",
]
HOURLY_VARIABLES = ["temperature_2m"]

PROVIDER_FORECAST = "open_meteo_ecmwf_ifs"
PROVIDER_HISTORICAL = "open_meteo_ecmwf_ifs_hist"


def _value(daily: dict[str, Any], key: str, i: int) -> float | None:
    """Return the i-th value of a daily series, or None when absent (never a default)."""
    series = daily.get(key)
    if not series or i >= len(series) or series[i] is None:
        return None
    return float(series[i])


def hourly_temperature_extremes(
    hourly: dict[str, Any],
) -> dict[date, tuple[float | None, float | None]]:
    """{local day: (max, min)} of hourly temperature_2m, grouped by the date prefix of `time`.

    A day without exactly 24 non-null hourly values maps to (None, None).
    """
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    by_day: dict[date, list[float | None]] = defaultdict(list)
    for i, t in enumerate(times):
        try:
            d = datetime.strptime(str(t)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        v = temps[i] if i < len(temps) else None
        by_day[d].append(None if v is None else float(v))
    out: dict[date, tuple[float | None, float | None]] = {}
    for d, vals in by_day.items():
        clean = [v for v in vals if v is not None]
        if len(vals) == HOURS_PER_DAY and len(clean) == HOURS_PER_DAY:
            out[d] = (max(clean), min(clean))
        else:
            out[d] = (None, None)
    return out


def parse_payload(payload: dict[str, Any], provider_name: str) -> list[RawDailyWeather]:
    """One Open-Meteo location payload -> one RawDailyWeather per daily `time` entry."""
    daily = payload.get("daily") or {}
    extremes = hourly_temperature_extremes(payload.get("hourly") or {})
    results: list[RawDailyWeather] = []
    incomplete: list[str] = []
    for i, dt_str in enumerate(daily.get("time", [])):
        try:
            rec_date = datetime.strptime(dt_str, "%Y-%m-%d").date()
        except (TypeError, ValueError) as e:
            logger.warn("weather_parse_row_error", index=i, error=str(e))
            continue
        t_max, t_min = extremes.get(rec_date, (None, None))
        if t_max is None:
            incomplete.append(dt_str)
        results.append(
            RawDailyWeather(
                record_date=rec_date,
                temp_max=t_max,
                temp_min=t_min,
                temp_mean=_value(daily, "temperature_2m_mean", i),
                rh_mean=_value(daily, "relative_humidity_2m_mean", i),
                rh_min=_value(daily, "relative_humidity_2m_min", i),
                wind_max=_value(daily, "wind_speed_10m_max", i),
                precip_sum=_value(daily, "precipitation_sum", i),
                et0=_value(daily, "et0_fao_evapotranspiration", i),
                soil_moisture=_value(daily, "soil_moisture_0_to_7cm_mean", i),
                provider=provider_name,
            )
        )
    if incomplete:
        logger.warn(
            "weather_days_missing_hourly_temperature",
            count=len(incomplete),
            dates=incomplete,
            lat=payload.get("latitude"),
            lon=payload.get("longitude"),
        )
    return results


def count_missing_temp(per_location: Sequence[Sequence[RawDailyWeather]]) -> int:
    """District-days whose hourly-derived temp_max is missing."""
    return sum(1 for recs in per_location for r in recs if r.temp_max is None)


class OpenMeteoWeatherProvider(WeatherProvider):
    """ECMWF IFS HRES daily weather from the Forecast API (recent days + forecast) and the
    Historical Forecast API (archive of the same model runs), both with identical derivation."""

    def __init__(
        self,
        forecast_url: str = settings.OPEN_METEO_WEATHER_URL,
        historical_url: str = settings.OPEN_METEO_HISTORICAL_FORECAST_URL,
    ):
        self.forecast_url = forecast_url
        self.historical_url = historical_url

    async def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        return await get_json(url, params)

    @staticmethod
    def base_params(coords: Sequence[tuple[float, float]]) -> dict[str, Any]:
        return {
            "latitude": ",".join(f"{lat:.4f}" for lat, _ in coords),
            "longitude": ",".join(f"{lon:.4f}" for _, lon in coords),
            "models": WEATHER_MODEL,
            "daily": ",".join(DAILY_VARIABLES),
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": TIMEZONE,
        }

    async def _fetch(
        self,
        url: str,
        coords: Sequence[tuple[float, float]],
        extra: dict[str, Any],
        provider_name: str,
    ) -> list[list[RawDailyWeather]]:
        if not coords:
            return []
        data = await self._get_json(url, {**self.base_params(coords), **extra})
        payloads = data if isinstance(data, list) else [data]
        if len(payloads) != len(coords):
            raise ValueError(
                f"Open-Meteo returned {len(payloads)} locations for {len(coords)} requested"
            )
        return [parse_payload(p, provider_name) for p in payloads]

    async def fetch_weather_forecast_batch(
        self,
        coords: Sequence[tuple[float, float]],
        past_days: int = 3,
        forecast_days: int = 3,
    ) -> list[list[RawDailyWeather]]:
        """Daily weather for many points in ONE request (Open-Meteo multi-location).

        Returns one list per input coordinate, in the same order.
        """
        return await self._fetch(
            self.forecast_url,
            coords,
            {"past_days": past_days, "forecast_days": forecast_days},
            PROVIDER_FORECAST,
        )

    async def fetch_weather_forecast(
        self, lat: float, lon: float, past_days: int = 3, forecast_days: int = 3
    ) -> list[RawDailyWeather]:
        return (await self.fetch_weather_forecast_batch([(lat, lon)], past_days, forecast_days))[0]

    async def fetch_historical_weather_batch(
        self,
        coords: Sequence[tuple[float, float]],
        start_date: date,
        end_date: date,
    ) -> list[list[RawDailyWeather]]:
        """Historical Forecast API (`models=ecmwf_ifs`), the archive the training data matches."""
        return await self._fetch(
            self.historical_url,
            coords,
            {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            PROVIDER_HISTORICAL,
        )

    async def fetch_historical_weather(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> list[RawDailyWeather]:
        return (await self.fetch_historical_weather_batch([(lat, lon)], start_date, end_date))[0]
