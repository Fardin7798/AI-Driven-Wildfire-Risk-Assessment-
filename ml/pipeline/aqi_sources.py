"""Shared readers and cleaning rules for the AQI pipeline (CAMS, CPCB stations, NASA POWER).

CAMS (Open-Meteo, hourly, Asia/Kolkata, one file per district `data/raw/cams/<region_id>.csv.gz`):
  * Invalid hourly values become missing hours (never clipped): negative concentrations of any
    pollutant, and CAMS PM10 >= 3270 µg/m³ (the CAMS PM10 ceiling value).
  * Daily value = 24-hour mean of the calendar day, valid only with >= 16 valid hours (CPCB
    minimum); otherwise missing. Nothing is filled or interpolated.

CPCB stations (OpenAQ v3 daily aggregates, `data/raw/openaq/sensors/<sensor_id>.csv`, local IST
date). A station day is excluded when: value missing, pct_complete < 75, value <= 0,
value == 985 (CPCB analyser ceiling, recurs exactly), value > 999, or the day is inside a run of
>= 5 identical consecutive daily values (stuck sensor; runs found on the full series).

PM2.5 sub-index: `app.domain.aqi.calculate_sub_index` (the same function production uses).
District ids: region_id = GADM 4.1 level-2 feature index + 1; names are checked against GADM.
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domain.aqi import calculate_sub_index  # noqa: E402

# CAMS column -> short key
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
WEATHER = ["temp_max", "temp_mean", "rh_mean", "wind_max", "precip_sum"]

MIN_PCT_COMPLETE = 75.0
STUCK_RUN_DAYS = 5
STATION_CEILING = 985.0
STATION_MAX = 999.0
EXCLUSION_RULES = (
    "missing_value",
    "pct_complete_lt_75",
    "value_le_0",
    "value_eq_985",
    "value_gt_999",
    "stuck_run_ge_5",
)

# Station data (OpenAQ CPCB) exists only for 2022-08..2022-10 and 2025-02-19 onwards, so the
# tuning split is: train = everything before 2025-07-01, val = 2025-07..2025-10. The test year is
# scored month by month with an expanding window (ml/train/train_aqi_station.py).
SPLITS = {
    "train": (date(1900, 1, 1), date(2025, 6, 30)),
    "val": (date(2025, 7, 1), date(2025, 10, 31)),
    "test": (date(2025, 11, 1), date(2026, 10, 28)),
}
SEASONS = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "pre_monsoon",
    4: "pre_monsoon",
    5: "pre_monsoon",
    6: "monsoon",
    7: "monsoon",
    8: "monsoon",
    9: "monsoon",
    10: "post_monsoon",
    11: "post_monsoon",
}


# ---------------------------------------------------------------- CAMS
def invalid_hours(hourly: pd.DataFrame) -> pd.DataFrame:
    """Boolean frame: hourly values that are physically invalid (negative, PM10 at ceiling)."""
    bad = hourly < 0
    bad["pm10"] |= hourly["pm10"] >= CAMS_PM10_CEILING
    return bad


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
    return daily_pm25.map(lambda v: np.nan if pd.isna(v) else float(calculate_sub_index("pm25", v)))


def daily_table(hourly: pd.DataFrame) -> pd.DataFrame:
    """Hourly CAMS frame (DatetimeIndex, short-key columns, µg/m³, invalid hours already NaN)
    -> daily frame with <p>_mean for all six pollutants and pm25_si. Index: datetime.date."""
    out = pd.DataFrame({f"{p}_mean": daily_mean_24h(hourly[p]) for p in POLLUTANTS.values()})
    out["pm25_si"] = pm25_sub_index(out["pm25_mean"])
    return out


def read_cams(path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Hourly CAMS file -> (frame with invalid hours set to NaN, counts of invalidated hours)."""
    df = pd.read_csv(path)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("time")))
    df = df.rename(columns=POLLUTANTS)[list(POLLUTANTS.values())]
    bad = invalid_hours(df)
    counts = {
        "negative": int((df < 0).sum().sum()),
        "pm10_ceiling": int((df["pm10"] >= CAMS_PM10_CEILING).sum()),
    }
    return df.mask(bad), counts


# ---------------------------------------------------------------- CPCB stations
def stuck_mask(d: pd.DataFrame) -> pd.Series:
    """True for days inside a run of >= STUCK_RUN_DAYS identical values on consecutive dates."""
    dt = pd.to_datetime(d["date"])
    brk = (d["value"] != d["value"].shift()) | (dt.diff() != pd.Timedelta(days=1))
    run = brk.cumsum()
    return run.map(run.value_counts()) >= STUCK_RUN_DAYS


def station_exclusions(d: pd.DataFrame) -> dict[str, pd.Series]:
    """Named exclusion masks for one sensor's daily series sorted by date (True = excluded)."""
    v = d["value"]
    return {
        "missing_value": v.isna(),
        "pct_complete_lt_75": ~(d["pct_complete"] >= MIN_PCT_COMPLETE),
        "value_le_0": v <= 0,
        "value_eq_985": v == STATION_CEILING,
        "value_gt_999": v > STATION_MAX,
        "stuck_run_ge_5": stuck_mask(d),
    }


def clean_station_days(d: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply every exclusion rule to one sensor's daily file; return kept days and counts."""
    d = d.sort_values("date").reset_index(drop=True)
    masks = station_exclusions(d)
    drop = pd.Series(False, index=d.index)
    for m in masks.values():
        drop |= m
    return d[~drop].reset_index(drop=True), {k: int(m.sum()) for k, m in masks.items()}


def match_sensors(sensors: pd.DataFrame, gadm: dict, regions: pd.DataFrame, rids: set[int]):
    """region_id of the district polygon (among `rids`) covering each sensor; NaN if none,
    -1 if more than one."""
    feats = gadm["features"]
    meta = regions.set_index("region_id")
    polys, ids = [], []
    for rid in sorted(rids):
        pr = feats[rid - 1]["properties"]
        r = meta.loc[rid]
        if (pr["NAME_1"], pr["NAME_2"]) != (r["state"], r["district"]):
            raise ValueError(f"region {rid} {r['state']}/{r['district']} != GADM {pr['GID_2']}")
        polys.append(shape(feats[rid - 1]["geometry"]))
        ids.append(rid)
    tree = STRtree(polys)
    out = []
    for s in sensors.itertuples():
        pt = Point(float(s.lon), float(s.lat))
        hits = [ids[i] for i in tree.query(pt) if polys[i].covers(pt)]
        out.append(hits[0] if len(hits) == 1 else (np.nan if not hits else -1))
    return out


# ---------------------------------------------------------------- misc
def assign_split(dates: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=dates.index, dtype="object")
    for name, (lo, hi) in SPLITS.items():
        out[(dates >= lo) & (dates <= hi)] = name
    return out


def region_gadm_map(regions: pd.DataFrame, gadm_path: Path) -> dict[int, str]:
    """region_id -> GID_2. regions_centroids.csv numbers GADM features in file order (1-based,
    the order load_regions.py inserts them). GADM has duplicate state/district names (e.g. two
    "Anjaw"), so names cannot be the key; they are only checked against the ordinal match."""
    feats = json.loads(gadm_path.read_text())["features"]
    out = {}
    for r in regions.itertuples():
        pr = feats[int(r.region_id) - 1]["properties"]
        if (pr["NAME_1"], pr["NAME_2"]) != (r.state, r.district):
            raise ValueError(f"region {r.region_id} {r.state}/{r.district} != GADM {pr['GID_2']}")
        out[int(r.region_id)] = pr["GID_2"]
    return out
