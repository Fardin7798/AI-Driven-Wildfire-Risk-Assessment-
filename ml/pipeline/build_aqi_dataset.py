"""Build the district x day AQI forecasting table (targets: CPCB daily AQI at t+1, t+2, t+3).

Daily AQI rule (CPCB National AQI, 2014), applied per district per calendar day (Asia/Kolkata):
  * PM2.5, PM10, NO2, SO2: 24-hour mean of the day's hourly values.
  * CO, O3: maximum of the 8-hour rolling means. Windows lie inside the calendar day (hours
    00-07 ... 16-23, 17 windows); a window needs >= 6 of its 8 hours (75%) to count.
  * A pollutant counts for the day only if it has >= 16 valid hours that day (CPCB minimum);
    otherwise it is missing for that day. Nothing is filled or interpolated.
  * Negative hourly concentrations (physically invalid; CAMS emits a few) are treated as
    invalid hours, not clipped.
  * The day's AQI is `app.domain.aqi.calculate_cpcb_aqi` on those values (µg/m³, CO converted
    µg/m³ -> mg/m³), i.e. the same function production uses: None unless >= 3 pollutants are
    available including PM2.5 or PM10.

Rows: one per (region_id, date t). Every feature is known at the end of day t:
  aqi_lag0..6 (aqi of t..t-6), <pollutant>_lag0..2 (24-h means, µg/m³, CO in µg/m³),
  aqi_roll7 / aqi_roll14 (mean AQI over t-6..t / t-13..t, complete windows only),
  POWER weather of day t and t-1, doy_sin/doy_cos, month, weekday, lat, lon.
Lags are calendar lags (a missing day is missing, never the previous available row).
Targets: aqi_t+1, aqi_t+2, aqi_t+3. Rows with any missing feature or target are dropped and
counted. Temporal split column `split`: train <= 2024-10-31, val 2024-11-01..2025-10-31,
test 2025-11-01..2026-10-28.

Baselines (written to baselines.json): persistence (aqi_t for every horizon) and seasonal-naive
(aqi_{t+h-7}, i.e. aqi_lag(7-h)); MAE and RMSE per horizon per split.

Inputs:
  --cams     dir of <region_id>.csv.gz hourly CAMS (download_air_history.py); every file is used
  --power    power_daily.parquet (download_power_history.py), keyed by gadm_id
  --regions  CSV region_id,district,state,lat,lon
  --gadm     GADM 4.1 level-2 GeoJSON (maps state/district names to gadm_id for POWER)
Outputs (gitignored): <out-dir>/aqi_dataset.parquet, <out-dir>/baselines.json
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domain.aqi import calculate_cpcb_aqi  # noqa: E402

# CAMS column -> CPCB key
POLLUTANTS = {
    "pm2_5": "pm25",
    "pm10": "pm10",
    "nitrogen_dioxide": "no2",
    "sulphur_dioxide": "so2",
    "carbon_monoxide": "co",
    "ozone": "o3",
}
MEAN_24H = ["pm25", "pm10", "no2", "so2"]
MAX_8H = ["co", "o3"]
MIN_VALID_HOURS = 16
MIN_WINDOW_HOURS = 6
WEATHER = ["temp_max", "temp_mean", "rh_mean", "wind_max", "precip_sum"]
HORIZONS = (1, 2, 3)
AQI_LAGS = range(7)
POLLUTANT_LAGS = range(3)
SPLITS = {
    "train": (date(1900, 1, 1), date(2024, 10, 31)),
    "val": (date(2024, 11, 1), date(2025, 10, 31)),
    "test": (date(2025, 11, 1), date(2026, 10, 28)),
}


# ---------------------------------------------------------------- daily aggregation
def _day_matrix(hourly: pd.Series) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Reindex an hourly series to whole days and return (days, array[n_days, 24])."""
    idx = pd.DatetimeIndex(hourly.index)
    start, end = idx.min().normalize(), idx.max().normalize() + pd.Timedelta(hours=23)
    full = pd.date_range(start, end, freq="h")
    s = hourly[~idx.duplicated()].reindex(full)
    vals = s.to_numpy(dtype=float).copy()
    vals[vals < 0] = np.nan
    days = pd.date_range(start, end.normalize(), freq="D")
    return days, vals.reshape(len(days), 24)


def daily_mean_24h(hourly: pd.Series) -> pd.Series:
    """24-h mean per calendar day; NaN when fewer than MIN_VALID_HOURS valid hours."""
    days, m = _day_matrix(hourly)
    n = np.isfinite(m).sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(m, axis=1)
    mean[n < MIN_VALID_HOURS] = np.nan
    return pd.Series(mean, index=days.date)


def daily_max_8h(hourly: pd.Series) -> pd.Series:
    """Max of within-day 8-h rolling means; NaN when fewer than MIN_VALID_HOURS valid hours."""
    days, m = _day_matrix(hourly)
    n = np.isfinite(m).sum(axis=1)
    win = np.lib.stride_tricks.sliding_window_view(m, 8, axis=1)  # (days, 17, 8)
    wn = np.isfinite(win).sum(axis=2)
    wsum = np.nansum(win, axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        wmean = np.where(wn >= MIN_WINDOW_HOURS, wsum / wn, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mx = np.nanmax(wmean, axis=1)
    mx[n < MIN_VALID_HOURS] = np.nan
    return pd.Series(mx, index=days.date)


def _aqi(vals: dict[str, float]) -> tuple[float, str | None]:
    clean = {k: (None if pd.isna(v) else float(v)) for k, v in vals.items()}
    res = calculate_cpcb_aqi(clean)
    return (float(res.aqi), res.prominent_pollutant) if res is not None else (np.nan, None)


def daily_table(hourly: pd.DataFrame) -> pd.DataFrame:
    """Hourly CAMS frame (DatetimeIndex, CPCB-key columns, µg/m³) -> daily frame.

    Columns: <p>_mean (24-h mean, all six), co_8h, o3_8h, aqi, prominent. Index: datetime.date.
    """
    out = pd.DataFrame({f"{p}_mean": daily_mean_24h(hourly[p]) for p in POLLUTANTS.values()})
    for p in MAX_8H:
        out[f"{p}_8h"] = daily_max_8h(hourly[p])
    results = [
        _aqi(
            {
                "pm25": r.pm25_mean,
                "pm10": r.pm10_mean,
                "no2": r.no2_mean,
                "so2": r.so2_mean,
                "co": r.co_8h / 1000.0,  # µg/m³ -> mg/m³ (CPCB CO breakpoints)
                "o3": r.o3_8h,
            }
        )
        for r in out.itertuples()
    ]
    out["aqi"] = [a for a, _ in results]
    out["prominent"] = [p for _, p in results]
    return out


def read_cams(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("time")))
    return df.rename(columns=POLLUTANTS)[list(POLLUTANTS.values())]


# ---------------------------------------------------------------- features / targets
def add_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add lag/rolling/target/calendar columns to a calendar-complete panel.

    `panel` has one row per (region_id, date) with no gaps in date per region, sorted.
    Only shifts by +k (past) feed features; shifts by -h feed targets only.
    """
    p = panel.sort_values(["region_id", "date"]).reset_index(drop=True)
    g = p.groupby("region_id", sort=False)
    new: dict[str, pd.Series] = {}
    for k in AQI_LAGS:
        new[f"aqi_lag{k}"] = g["aqi"].shift(k)
    for pol in POLLUTANTS.values():
        for k in POLLUTANT_LAGS:
            new[f"{pol}_lag{k}"] = g[f"{pol}_mean"].shift(k)
    for w in (7, 14):
        new[f"aqi_roll{w}"] = g["aqi"].transform(lambda s, w=w: s.rolling(w, min_periods=w).mean())
    for col in WEATHER:
        new[col] = p[col]
        new[f"{col}_lag1"] = g[col].shift(1)
    dt = pd.to_datetime(p["date"])
    doy = dt.dt.day_of_year.astype(float)
    new["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    new["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    new["month"] = dt.dt.month
    new["weekday"] = dt.dt.day_of_week
    for h in HORIZONS:
        new[f"aqi_t+{h}"] = g["aqi"].shift(-h)
    return pd.concat([p[["region_id", "date", "lat", "lon"]], pd.DataFrame(new)], axis=1)


def feature_columns() -> list[str]:
    cols = [f"aqi_lag{k}" for k in AQI_LAGS]
    cols += [f"{p}_lag{k}" for p in POLLUTANTS.values() for k in POLLUTANT_LAGS]
    cols += ["aqi_roll7", "aqi_roll14"]
    cols += [c for w in WEATHER for c in (w, f"{w}_lag1")]
    cols += ["doy_sin", "doy_cos", "month", "weekday", "lat", "lon"]
    return cols


TARGETS = [f"aqi_t+{h}" for h in HORIZONS]


def assign_split(dates: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=dates.index, dtype="object")
    for name, (lo, hi) in SPLITS.items():
        out[(dates >= lo) & (dates <= hi)] = name
    return out


# ---------------------------------------------------------------- baselines
def baselines(df: pd.DataFrame) -> dict:
    res: dict = {}
    for split, part in df.groupby("split"):
        res[split] = {}
        for h in HORIZONS:
            y = part[f"aqi_t+{h}"].to_numpy(float)
            for name, col in (("persistence", "aqi_lag0"), ("seasonal_naive", f"aqi_lag{7 - h}")):
                e = part[col].to_numpy(float) - y
                res[split].setdefault(name, {})[f"h{h}"] = {
                    "mae": round(float(np.mean(np.abs(e))), 3),
                    "rmse": round(float(np.sqrt(np.mean(e**2))), 3),
                }
    return res


# ---------------------------------------------------------------- main
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


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--cams", type=Path, default=Path("data/raw/cams"))
    ap.add_argument("--power", type=Path, default=Path("data/raw/power_aqi/power_daily.parquet"))
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("data/processed/aqi"))
    args = ap.parse_args()

    regions = pd.read_csv(args.regions)
    gmap = region_gadm_map(regions, args.gadm)
    meta = regions.set_index("region_id")

    files = sorted(args.cams.glob("*.csv.gz"), key=lambda f: int(f.name.split(".")[0]))
    if not files:
        raise SystemExit(f"no CAMS files in {args.cams}")
    daily_frames = []
    neg_hours = 0
    for f in files:
        rid = int(f.name.split(".")[0])
        hourly = read_cams(f)
        neg_hours += int((hourly < 0).sum().sum())
        d = daily_table(hourly)
        d.index.name = "date"
        d = d.reset_index()
        d.insert(0, "region_id", rid)
        daily_frames.append(d)
    daily = pd.concat(daily_frames, ignore_index=True)

    # daily validity stats (region-days with hourly data started)
    started = daily[daily[[f"{p}_mean" for p in POLLUTANTS.values()]].notna().any(axis=1)]
    day_stats = {
        "region_days_with_any_data": int(len(started)),
        "region_days_valid_aqi": int(started["aqi"].notna().sum()),
        "pollutant_days_below_16h": {
            p: int(started[f"{p}_mean"].isna().sum()) for p in POLLUTANTS.values()
        },
        "negative_hourly_values_invalidated": neg_hours,
        "prominent_pollutant_share": {
            k: round(float(v), 4)
            for k, v in started["prominent"].value_counts(normalize=True).items()
        },
    }

    power = pd.read_parquet(args.power)
    power["date"] = pd.to_datetime(power["date"]).dt.date
    inv = {v: k for k, v in gmap.items()}
    power = power[power["gadm_id"].isin(set(gmap.values()))].copy()
    power["region_id"] = power.pop("gadm_id").map(inv)

    panel = daily.merge(power, on=["region_id", "date"], how="left")
    panel["lat"] = panel["region_id"].map(meta["lat"])
    panel["lon"] = panel["region_id"].map(meta["lon"])
    feats = add_features(panel)
    feats["split"] = assign_split(feats["date"])

    fcols, total = feature_columns(), len(feats)
    in_split = feats[feats["split"].notna()]
    groups = {
        "target_aqi_missing": TARGETS,
        "aqi_lag_missing": [f"aqi_lag{k}" for k in AQI_LAGS],
        "aqi_rolling_missing": ["aqi_roll7", "aqi_roll14"],
        "pollutant_lag_missing": [c for c in fcols if c.split("_lag")[0] in POLLUTANTS.values()],
        "weather_missing": [c for c in fcols if c.split("_lag")[0] in WEATHER],
    }
    remaining = in_split
    first_reason: dict[str, int] = {}
    any_reason: dict[str, int] = {}
    for name, cols in groups.items():
        any_reason[name] = int(in_split[cols].isna().any(axis=1).sum())
        bad = remaining[cols].isna().any(axis=1)
        first_reason[name] = int(bad.sum())
        remaining = remaining[~bad]
    out = remaining.dropna(subset=fcols + TARGETS).copy()
    assert len(out) == len(remaining)
    for c in [f"aqi_lag{k}" for k in AQI_LAGS] + TARGETS:
        out[c] = out[c].astype("int16")
    out = out[["region_id", "date", "split", *fcols, *TARGETS]].reset_index(drop=True)

    report = {
        "rule": "CPCB daily AQI: 24h mean PM2.5/PM10/NO2/SO2, max 8h mean CO/O3, >=16 valid h",
        "n_cams_files": len(files),
        "daily": day_stats,
        "rows": {
            "panel_region_days": total,
            "outside_split_window": total - len(in_split),
            "candidates_in_splits": len(in_split),
            "kept": len(out),
            "dropped": len(in_split) - len(out),
            "dropped_by_first_reason": first_reason,
            "rows_missing_group_any": any_reason,
        },
        "splits": {
            s: {
                "rows": int(len(x)),
                "districts": int(x["region_id"].nunique()),
                "date_min": str(x["date"].min()),
                "date_max": str(x["date"].max()),
                "aqi_target_h1_min": int(x["aqi_t+1"].min()),
                "aqi_target_h1_max": int(x["aqi_t+1"].max()),
                "aqi_target_h1_mean": round(float(x["aqi_t+1"].mean()), 2),
            }
            for s, x in out.groupby("split")
        },
        "districts": int(out["region_id"].nunique()),
        "baselines": baselines(out),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out_dir / "aqi_dataset.parquet", index=False)
    (args.out_dir / "baselines.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
