"""District AQI features: the ONE implementation used by the training dataset builder
(ml/pipeline/build_aqi_station_dataset.py) and by live forecasting (app/ml/aqi_station_b.py).

CAMS (Open-Meteo air-quality, hourly, district centroid, timezone Asia/Kolkata):
  * Invalid hourly values become missing hours (never clipped): negative concentrations of any
    pollutant, and CAMS PM10 >= 3270 µg/m³ (the CAMS PM10 ceiling value).
  * Daily value = 24-hour mean of the IST calendar day, valid only with >= 16 valid hours (CPCB
    minimum); otherwise missing. Nothing is filled or interpolated.
  * PM2.5 sub-index: `app.domain.aqi.calculate_sub_index` (CPCB breakpoints) of the daily mean.

District features at day t (calendar lags: a missing day is missing, never the previous row):
  cams_pm25_si_lag0..6, cams_pm25_si_roll7/14 (>= 5/10 valid days),
  cams_<pollutant>_lag0..2 (24-h means, µg/m³), weather of day t and t-1
  (temp_max, temp_mean, rh_mean, wind_max km/h, precip_sum; Open-Meteo daily, IST days),
  calendar doy_sin, doy_cos, month, weekday of day t.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable

import numpy as np
import pandas as pd

from app.domain.aqi import calculate_sub_index

# Open-Meteo CAMS variable -> short key
POLLUTANTS = {
    "pm2_5": "pm25",
    "pm10": "pm10",
    "nitrogen_dioxide": "no2",
    "sulphur_dioxide": "so2",
    "carbon_monoxide": "co",
    "ozone": "o3",
}
MIN_VALID_HOURS = 16
CAMS_PM10_CEILING = 3270.0

# Open-Meteo daily variable -> short key (default units: deg C, %, km/h, mm)
WEATHER_DAILY = {
    "temperature_2m_max": "temp_max",
    "temperature_2m_mean": "temp_mean",
    "relative_humidity_2m_mean": "rh_mean",
    "wind_speed_10m_max": "wind_max",
    "precipitation_sum": "precip_sum",
}
WEATHER = list(WEATHER_DAILY.values())

HORIZONS = (1, 2, 3)
SI_LAGS = range(7)
POLLUTANT_LAGS = range(3)
CAMS_ROLL = {7: 5, 14: 10}  # window: minimum valid days
# Days of history before day t that the district features read (roll14 = t-13..t).
HISTORY_DAYS = max(max(CAMS_ROLL), max(SI_LAGS) + 1, max(POLLUTANT_LAGS) + 1) - 1
CALENDAR = ["doy_sin", "doy_cos", "month", "weekday"]


# ---------------------------------------------------------------- CAMS hourly -> daily
def invalid_hours(hourly: pd.DataFrame) -> pd.DataFrame:
    """Boolean frame: hourly values that are physically invalid (negative, PM10 at ceiling)."""
    bad = hourly < 0
    bad["pm10"] |= hourly["pm10"] >= CAMS_PM10_CEILING
    return bad


def clean_hourly(raw: pd.DataFrame) -> pd.DataFrame:
    """Hourly frame with a `time` column and Open-Meteo variable columns -> DatetimeIndex frame
    with short-key columns, invalid hours set to NaN."""
    df = raw.copy()
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("time")))
    df = df.rename(columns=POLLUTANTS)[list(POLLUTANTS.values())].astype(float)
    return df.mask(invalid_hours(df))


def daily_mean_24h(hourly: pd.Series) -> pd.Series:
    """24-h mean per calendar day; NaN when fewer than MIN_VALID_HOURS valid hours.

    Hours absent from the index and NaN hours are missing. Invalid values must already be NaN.
    """
    idx = pd.DatetimeIndex(hourly.index)
    start, end = idx.min().normalize(), idx.max().normalize() + pd.Timedelta(hours=23)
    full = pd.date_range(start, end, freq="h")
    m = hourly[~idx.duplicated()].reindex(full).to_numpy(dtype=float).reshape(-1, 24)
    n = np.isfinite(m).sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(m, axis=1)
    mean[n < MIN_VALID_HOURS] = np.nan
    days = pd.date_range(start, end.normalize(), freq="D")
    return pd.Series(mean, index=days.date)


def pm25_sub_index(daily_pm25: pd.Series) -> pd.Series:
    """CPCB PM2.5 sub-index of daily 24-h means; NaN stays NaN."""

    def si(v: float) -> float:
        out = None if pd.isna(v) else calculate_sub_index("pm25", v)
        return np.nan if out is None else float(out)

    return daily_pm25.map(si)


def daily_table(hourly: pd.DataFrame) -> pd.DataFrame:
    """Hourly CAMS frame (DatetimeIndex, short-key columns, µg/m³, invalid hours already NaN)
    -> daily frame with <p>_mean for all six pollutants and pm25_si. Index: datetime.date."""
    out = pd.DataFrame({f"{p}_mean": daily_mean_24h(hourly[p]) for p in POLLUTANTS.values()})
    out["pm25_si"] = pm25_sub_index(out["pm25_mean"])
    return out


# ---------------------------------------------------------------- panels and features
def calendar_panel(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Reindex each `key` group to every calendar day between its first and last date."""
    parts = []
    for k, part in df.groupby(key, sort=True):
        days = pd.date_range(min(part["date"]), max(part["date"]), freq="D").date
        full = pd.DataFrame({key: k, "date": days})
        parts.append(full.merge(part, on=[key, "date"], how="left"))
    return pd.concat(parts, ignore_index=True)


def district_panel(cams_daily: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """CAMS daily rows (region_id, date, <p>_mean, pm25_si) + weather rows (region_id, date,
    WEATHER) -> calendar-complete district panel. Outer join: weather days before the first CAMS
    day still feed the t-1 weather lag; CAMS on those days stays NaN."""
    return calendar_panel(
        cams_daily.merge(weather, on=["region_id", "date"], how="outer"), "region_id"
    )


def rolling_mean(g, col: str, w: int, min_n: int) -> pd.Series:
    return g[col].transform(lambda s: s.rolling(w, min_periods=min_n).mean())


def district_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Calendar-complete district panel (region_id, date, <p>_mean, pm25_si, weather) ->
    district features at day t, plus reference CAMS sub-index on t+h (`ref_cams_si_t+h`, a
    training comparison column, never a model input)."""
    p = panel.sort_values(["region_id", "date"]).reset_index(drop=True)
    g = p.groupby("region_id", sort=False)
    new: dict[str, pd.Series] = {}
    for k in SI_LAGS:
        new[f"cams_pm25_si_lag{k}"] = g["pm25_si"].shift(k)
    for w, n in CAMS_ROLL.items():
        new[f"cams_pm25_si_roll{w}"] = rolling_mean(g, "pm25_si", w, n)
    for pol in POLLUTANTS.values():
        for k in POLLUTANT_LAGS:
            new[f"cams_{pol}_lag{k}"] = g[f"{pol}_mean"].shift(k)
    for col in WEATHER:
        new[col] = p[col]
        new[f"{col}_lag1"] = g[col].shift(1)
    for h in HORIZONS:
        new[f"ref_cams_si_t+{h}"] = g["pm25_si"].shift(-h)
    return pd.concat([p[["region_id", "date"]], pd.DataFrame(new)], axis=1)


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features of day t (`date` column) in place and return df."""
    dt = pd.to_datetime(df["date"])
    doy = dt.dt.day_of_year.astype(float)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["month"] = dt.dt.month
    df["weekday"] = dt.dt.day_of_week
    return df


def weather_frame(region_id: int, dates: Iterable, values: dict[str, Iterable]) -> pd.DataFrame:
    """Daily weather series (short keys) -> (region_id, date, WEATHER) rows; None stays NaN."""
    out = pd.DataFrame({c: pd.Series(list(values[c]), dtype=float) for c in WEATHER})
    out.insert(0, "date", pd.to_datetime(pd.Series(list(dates))).dt.date)
    out.insert(0, "region_id", region_id)
    return out
