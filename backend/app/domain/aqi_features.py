"""District AQI features: the ONE implementation used by the training dataset builder
(ml/pipeline/build_aqi_station_dataset.py) and by live forecasting (app/ml/aqi_station_b.py),
plus the CPCB averaging of the live current AQI (app/providers/open_meteo_air.py).

CAMS (Open-Meteo air-quality, hourly, district centroid, timezone Asia/Kolkata):
  * Invalid hourly values become missing hours (never clipped): negative concentrations of any
    pollutant, and CAMS PM10 >= 3270 µg/m³ (the CAMS PM10 ceiling value).
  * Daily value = 24-hour mean of the IST calendar day, valid only with >= 16 valid hours (CPCB
    minimum); otherwise missing. Nothing is filled or interpolated.
  * PM2.5 sub-index: `app.domain.aqi.calculate_sub_index` (CPCB breakpoints) of the daily mean.

Current AQI (live, `current_concentrations`): CPCB averaging over the trailing 24 h ending at the
latest whole UTC hour (24 hourly values). Reference: CPCB, "How is AQI calculated?"
https://airquality.cpcb.gov.in/ccr_docs/How_AQI_Calculated.pdf (sub-indices from 24-hourly
averages, 8-hourly for CO and O3; >= 16 hours of data per sub-index; running averages, e.g. AQI at
6 am uses data from 6 am the previous day).
  * PM2.5, PM10, NO2, SO2: 24-h mean, valid only with >= 16 valid hours, else missing.
  * CO, O3: maximum of the 8-h running means whose 8 hours all lie inside the 24-h window; an 8-h
    window counts only with >= 6 valid hours. The 6-of-8 rule is a common convention (75 %
    completeness), NOT a CPCB rule; the CPCB note says only "8-hourly", so taking the maximum
    8-h mean of the window is likewise a convention. No valid 8-h window -> missing.
  Nothing is filled or interpolated; a missing pollutant stays missing.

District features at day t (calendar lags: a missing day is missing, never the previous row):
  cams_pm25_si_lag0..6, cams_pm25_si_roll7/14 (>= 5/10 valid days),
  cams_<pollutant>_lag0..2 (24-h means, µg/m³), weather of day t and t-1
  (temp_max, temp_mean, rh_mean, wind_max km/h, precip_sum; Open-Meteo daily, IST days),
  calendar doy_sin, doy_cos, month, weekday of day t.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

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

# Current AQI averaging (see module docstring)
CPCB_AQI_DOC_URL = "https://airquality.cpcb.gov.in/ccr_docs/How_AQI_Calculated.pdf"
CURRENT_WINDOW_HOURS = 24
MEAN_24H_POLLUTANTS = ("pm25", "pm10", "no2", "so2")
MAX_8H_POLLUTANTS = ("co", "o3")
RUNNING_WINDOW_HOURS = 8
RUNNING_MIN_VALID_HOURS = 6  # common convention, not a CPCB rule
# Provider label of rows stored with this averaging (older rows labelled "copernicus_cams" were
# instantaneous values and get no averaging metadata).
CAMS_AVERAGED_PROVIDER = "copernicus_cams_cpcb_avg"

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


def row_means(m: np.ndarray, min_valid: int) -> np.ndarray:
    """Mean of each row of a 2-D array over its finite values; NaN where a row has fewer than
    `min_valid` finite values."""
    n = np.isfinite(m).sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(m, axis=1)
    mean[n < min_valid] = np.nan
    return mean


def daily_mean_24h(hourly: pd.Series) -> pd.Series:
    """24-h mean per calendar day; NaN when fewer than MIN_VALID_HOURS valid hours.

    Hours absent from the index and NaN hours are missing. Invalid values must already be NaN.
    """
    idx = pd.DatetimeIndex(hourly.index)
    start, end = idx.min().normalize(), idx.max().normalize() + pd.Timedelta(hours=23)
    full = pd.date_range(start, end, freq="h")
    m = hourly[~idx.duplicated()].reindex(full).to_numpy(dtype=float).reshape(-1, 24)
    mean = row_means(m, MIN_VALID_HOURS)
    days = pd.date_range(start, end.normalize(), freq="D")
    return pd.Series(mean, index=days.date)


def current_window_end(now: datetime) -> datetime:
    """Latest whole UTC hour at or before `now` (aware) -> naive UTC hour ending the 24-h window."""
    return now.astimezone(UTC).replace(minute=0, second=0, microsecond=0, tzinfo=None)


def current_window_start(end: datetime) -> datetime:
    """First hourly timestamp of the 24-h window ending at `end` (24 values, end inclusive)."""
    return end - timedelta(hours=CURRENT_WINDOW_HOURS - 1)


def current_concentrations(hourly: pd.DataFrame, end: datetime) -> dict[str, float | None]:
    """CPCB-averaged concentrations over the 24-h window ending at `end` (see module docstring).

    `hourly`: clean_hourly frame (naive UTC DatetimeIndex, short keys, invalid hours NaN). Hours
    outside the window are ignored; hours absent from it are missing. Units are kept as given.
    """
    window = pd.date_range(current_window_start(end), end, freq="h")
    h = hourly[~pd.DatetimeIndex(hourly.index).duplicated()].reindex(window)
    out: dict[str, float | None] = {}
    for p in MEAN_24H_POLLUTANTS:
        v = row_means(h[p].to_numpy(dtype=float)[None, :], MIN_VALID_HOURS)[0]
        out[p] = None if np.isnan(v) else float(v)
    for p in MAX_8H_POLLUTANTS:
        runs = np.lib.stride_tricks.sliding_window_view(
            h[p].to_numpy(dtype=float), RUNNING_WINDOW_HOURS
        )
        means = row_means(runs, RUNNING_MIN_VALID_HOURS)
        out[p] = float(np.nanmax(means)) if np.isfinite(means).any() else None
    return out


MEAN_24H_METHOD = f"{CURRENT_WINDOW_HOURS}h mean, >= {MIN_VALID_HOURS} valid hours"
MAX_8H_METHOD = (
    f"max {RUNNING_WINDOW_HOURS}h running mean in window, each {RUNNING_WINDOW_HOURS}h window "
    f">= {RUNNING_MIN_VALID_HOURS} valid hours (common convention, not a CPCB rule)"
)


def current_averaging(end: datetime) -> dict[str, object]:
    """Averaging metadata for a value computed by `current_concentrations` with window `end`."""
    return {
        "window_start_utc": current_window_start(end).replace(tzinfo=UTC),
        "window_end_utc": end.replace(tzinfo=UTC),
        "window_hours": CURRENT_WINDOW_HOURS,
        "methods": {
            **dict.fromkeys(MEAN_24H_POLLUTANTS, MEAN_24H_METHOD),
            **dict.fromkeys(MAX_8H_POLLUTANTS, MAX_8H_METHOD),
        },
        "aqi_rule": "max sub-index; reported only with >= 3 pollutants incl. PM2.5 or PM10",
        "reference": CPCB_AQI_DOC_URL,
    }


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
