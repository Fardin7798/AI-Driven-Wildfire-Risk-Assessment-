"""Live forecasts of AQI model B (aqi_station_xgb_v3, no-station boosters h1..h3).

Forecast origin t = yesterday (IST), the latest complete IST day of CAMS; h1..h3 = t+1..t+3
(today, tomorrow, the day after). Inputs, requested exactly as the training downloads did
(ml/pipeline/download_air_history.py, download_weather_history.py):

  * CAMS: Open-Meteo air-quality API, hourly pm2_5, pm10, nitrogen_dioxide, sulphur_dioxide,
    carbon_monoxide, ozone, timezone Asia/Kolkata, start_date = t - HISTORY_DAYS, end_date = t.
  * Weather: Open-Meteo Forecast API daily (default best-match model, default units),
    timezone Asia/Kolkata, past_days = 2 (days t-1 and t). The Historical Forecast API used in
    training archives these same values.
  * Point: the district centroid as in training (regions_centroids.csv, 4 decimals), sent in the
    same text form; lat/lon features are those floats.

Features come only from `app.domain.aqi_features` (the code the training dataset was built
with). A district whose feature row has any missing value is skipped with the reason; nothing is
imputed. Predictions are clipped to [0, 500] and mapped to the CPCB category. Every forecast
carries `extrapolated` from the model's coverage.json.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.core.config import settings
from app.domain.aqi import get_aqi_category
from app.domain.aqi_features import (
    HISTORY_DAYS,
    HORIZONS,
    POLLUTANTS,
    WEATHER_DAILY,
    add_calendar,
    clean_hourly,
    daily_table,
    district_features,
    district_panel,
    weather_frame,
)
from app.ml.loader import AqiStationModel, model_loader
from app.providers.open_meteo_http import OpenMeteoQuotaExceeded, get_json

IST = ZoneInfo("Asia/Kolkata")
TIMEZONE = "Asia/Kolkata"
WEATHER_PAST_DAYS = 2  # days t-1 and t (t = yesterday)
AQI_MIN, AQI_MAX = 0.0, 500.0


def origin_day(now: datetime | None = None) -> date:
    """Forecast origin t: yesterday on the IST calendar."""
    now = now or datetime.now(IST)
    return now.astimezone(IST).date() - timedelta(days=1)


def format_coord(value: float) -> str:
    """Centroid coordinate as the training requests sent it (regions_centroids.csv text)."""
    return repr(round(float(value), 4))


def cams_params(lat: float, lon: float, origin: date) -> dict[str, Any]:
    return {
        "latitude": format_coord(lat),
        "longitude": format_coord(lon),
        "hourly": ",".join(POLLUTANTS),
        "start_date": (origin - timedelta(days=HISTORY_DAYS)).isoformat(),
        "end_date": origin.isoformat(),
        "timezone": TIMEZONE,
    }


def weather_params(lat: float, lon: float) -> dict[str, Any]:
    return {
        "latitude": format_coord(lat),
        "longitude": format_coord(lon),
        "daily": ",".join(WEATHER_DAILY),
        "past_days": WEATHER_PAST_DAYS,
        "timezone": TIMEZONE,
    }


def build_features(
    region_id: int,
    lat: float,
    lon: float,
    origin: date,
    cams_hourly: dict[str, list[Any]],
    weather_daily: dict[str, list[Any]],
) -> pd.Series:
    """Open-Meteo `hourly` (CAMS) and `daily` (weather) JSON blocks -> district feature row at
    day `origin` (all district, calendar and lat/lon columns; missing values stay NaN)."""
    first = origin - timedelta(days=HISTORY_DAYS)
    hourly = clean_hourly(pd.DataFrame(cams_hourly))
    hourly = hourly[(hourly.index.date >= first) & (hourly.index.date <= origin)]
    if hourly.empty:
        raise ValueError(f"no CAMS hours between {first} and {origin}")
    cams = daily_table(hourly)
    cams.index.name = "date"
    cams = cams.reset_index().assign(region_id=int(region_id))

    weather = weather_frame(
        int(region_id),
        weather_daily["time"],
        {short: weather_daily[om] for om, short in WEATHER_DAILY.items()},
    )
    weather = weather[(weather["date"] >= first) & (weather["date"] <= origin)]

    feats = district_features(district_panel(cams, weather))
    row = feats[feats["date"] == origin].copy()
    if len(row) != 1:
        raise ValueError(f"no feature row for {origin}")
    add_calendar(row)
    row["lat"] = float(lat)
    row["lon"] = float(lon)
    return row.iloc[0]


def missing_features(row: pd.Series, features: list[str]) -> list[str]:
    return [f for f in features if f not in row.index or pd.isna(row[f])]


def predict(model: AqiStationModel, row: pd.Series, origin: date) -> list[dict[str, Any]]:
    """Feature row without missing values -> forecasts for t+1..t+3."""
    import xgboost as xgb

    x = np.asarray([[float(row[f]) for f in model.feature_list]], dtype=float)
    dm = xgb.DMatrix(x, feature_names=model.feature_list)
    out = []
    for h in HORIZONS:
        raw = float(model.boosters[h].predict(dm)[0])
        aqi = float(np.clip(raw, AQI_MIN, AQI_MAX))
        out.append(
            {
                "target_date": (origin + timedelta(days=h)).isoformat(),
                "horizon_days": h,
                "pm25_si_pred": round(aqi, 1),
                "aqi_pred": int(round(aqi)),
                "aqi_category": get_aqi_category(int(round(aqi))),
                "model_version": model.model_version,
            }
        )
    return out


def coverage_entry(model: AqiStationModel, region_id: int) -> dict[str, Any] | None:
    for d in model.coverage["districts"]:
        if int(d["region_id"]) == int(region_id):
            return d
    return None


def _skip(region_id: int, origin: date, model_version: str, reason: str) -> dict[str, Any]:
    return {
        "region_id": int(region_id),
        "origin_date": origin.isoformat(),
        "model_version": model_version,
        "status": "skipped",
        "reason": reason,
        "forecasts": [],
    }


async def forecast_district(
    region_id: int,
    lat: float,
    lon: float,
    model: AqiStationModel | None = None,
    origin: date | None = None,
) -> dict[str, Any]:
    """Fetch live inputs for one district centroid and forecast h1..h3, or skip with a reason."""
    origin = origin or origin_day()
    model = model or model_loader.load_aqi_model()
    if model is None:
        return _skip(region_id, origin, settings.ACTIVE_AQI_MODEL, "model not loaded")
    cov = coverage_entry(model, region_id)
    if cov is None:
        return _skip(region_id, origin, model.model_version, "region not in model coverage")
    if (format_coord(lat), format_coord(lon)) != (
        format_coord(cov["lat"]),
        format_coord(cov["lon"]),
    ):
        return _skip(
            region_id,
            origin,
            model.model_version,
            f"centroid {format_coord(lat)},{format_coord(lon)} differs from the training "
            f"centroid {format_coord(cov['lat'])},{format_coord(cov['lon'])}",
        )

    try:
        air = await get_json(settings.OPEN_METEO_AIR_QUALITY_URL, cams_params(lat, lon, origin))
        wx = await get_json(settings.OPEN_METEO_WEATHER_URL, weather_params(lat, lon))
        row = build_features(region_id, lat, lon, origin, air["hourly"], wx["daily"])
    except OpenMeteoQuotaExceeded:
        raise  # the caller stops; retrying only extends the block
    except Exception as e:  # network, quota, malformed payload: no forecast, never a default
        return _skip(region_id, origin, model.model_version, f"input unavailable: {e}")

    missing = missing_features(row, model.feature_list)
    if missing:
        return _skip(
            region_id, origin, model.model_version, "missing features: " + ", ".join(missing)
        )

    forecasts = predict(model, row, origin)
    for f in forecasts:
        f["extrapolated"] = bool(cov["extrapolated"])
    return {
        "region_id": int(region_id),
        "origin_date": origin.isoformat(),
        "model_version": model.model_version,
        "status": "ok",
        "reason": None,
        "extrapolated": bool(cov["extrapolated"]),
        "nearest_training_station_km": cov["nearest_training_station_km"],
        "forecasts": forecasts,
    }
