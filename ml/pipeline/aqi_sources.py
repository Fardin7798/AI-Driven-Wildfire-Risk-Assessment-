"""Shared readers and cleaning rules for the AQI pipeline (CAMS, CPCB stations, weather).

CAMS (Open-Meteo, hourly, Asia/Kolkata, one file per district `data/raw/cams/<region_id>.csv.gz`):
the cleaning rules, 24-h daily means and PM2.5 sub-index live in `app.domain.aqi_features`, the
single implementation that live forecasting uses too; this module only reads the files.

CPCB stations (OpenAQ v3 daily aggregates, `data/raw/openaq/sensors/<sensor_id>.csv`, local IST
date). A station day is excluded when: value missing, pct_complete < 75, value <= 0,
value == 985 (CPCB analyser ceiling, recurs exactly), value > 999, or the day is inside a run of
>= 5 identical consecutive daily values (stuck sensor; runs found on the full series).

PM2.5 sub-index: `app.domain.aqi.calculate_sub_index` (the same function production uses).
District ids: region_id = GADM 4.1 level-2 feature index + 1; names are checked against GADM.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domain.aqi_features import (  # noqa: E402,F401  (re-exported for the builders)
    CAMS_PM10_CEILING,
    MIN_VALID_HOURS,
    POLLUTANTS,
    WEATHER,
    clean_hourly,
    daily_mean_24h,
    daily_table,
    invalid_hours,
    pm25_sub_index,
)

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
def read_cams(path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Hourly CAMS file -> (frame with invalid hours set to NaN, counts of invalidated hours)."""
    raw = pd.read_csv(path)
    vals = raw.rename(columns=POLLUTANTS)[list(POLLUTANTS.values())]
    counts = {
        "negative": int((vals < 0).sum().sum()),
        "pm10_ceiling": int((vals["pm10"] >= CAMS_PM10_CEILING).sum()),
    }
    return clean_hourly(raw), counts


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
