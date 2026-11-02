"""Build the district x day PM2.5 forecasting table (target: CPCB PM2.5 sub-index at t+1..t+3).

Target rule, applied per district per calendar day (Asia/Kolkata):
  * Daily PM2.5 = 24-hour mean of the day's hourly CAMS PM2.5, valid only with >= 16 valid hours
    (CPCB minimum); otherwise the day is missing. Nothing is filled or interpolated.
  * Target = CPCB PM2.5 sub-index of that daily mean (`app.domain.aqi.calculate_sub_index`, the
    same function production uses). PM10, NO2, SO2, CO, O3 and weather never enter the target;
    they are lagged input features only.
  * Invalid hourly values become missing hours (never clipped): negative concentrations of any
    pollutant, and CAMS PM10 >= 3270 µg/m³ (the CAMS PM10 ceiling value).

Rows: one per (region_id, date t). Every feature is known at the end of day t:
  pm25_si_lag0..6 (sub-index of t..t-6), <pollutant>_lag0..2 (24-h means of t..t-2, µg/m³,
  >= 16 valid hours each), pm25_si_roll7 / pm25_si_roll14 (mean sub-index over t-6..t /
  t-13..t, complete windows only), POWER weather of day t and t-1, doy_sin/doy_cos, month,
  weekday, lat, lon. Lags are calendar lags (a missing day is missing, never the previous row).
Targets: pm25_si_t+1, pm25_si_t+2, pm25_si_t+3. Rows with any missing feature or target are
dropped and counted. Temporal split column `split`: train <= 2024-10-31,
val 2024-11-01..2025-10-31, test 2025-11-01..2026-10-28.

Baselines (written to baselines.json): persistence (pm25_si of t for every horizon) and
seasonal-naive (pm25_si of t+h-7, i.e. pm25_si_lag(7-h)); MAE and RMSE per horizon per split,
plus test MAE per Indian season.

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
HORIZONS = (1, 2, 3)
SI_LAGS = range(7)
POLLUTANT_LAGS = range(3)
SPLITS = {
    "train": (date(1900, 1, 1), date(2024, 10, 31)),
    "val": (date(2024, 11, 1), date(2025, 10, 31)),
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


# ---------------------------------------------------------------- daily aggregation
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


# ---------------------------------------------------------------- features / targets
def add_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add lag/rolling/target/calendar columns to a calendar-complete panel.

    `panel` has one row per (region_id, date) with no gaps in date per region.
    Only shifts by +k (past) feed features; shifts by -h feed targets only.
    """
    p = panel.sort_values(["region_id", "date"]).reset_index(drop=True)
    g = p.groupby("region_id", sort=False)
    new: dict[str, pd.Series] = {}
    for k in SI_LAGS:
        new[f"pm25_si_lag{k}"] = g["pm25_si"].shift(k)
    for pol in POLLUTANTS.values():
        for k in POLLUTANT_LAGS:
            new[f"{pol}_lag{k}"] = g[f"{pol}_mean"].shift(k)
    for w in (7, 14):
        new[f"pm25_si_roll{w}"] = g["pm25_si"].transform(
            lambda s, w=w: s.rolling(w, min_periods=w).mean()
        )
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
        new[f"pm25_si_t+{h}"] = g["pm25_si"].shift(-h)
    return pd.concat([p[["region_id", "date", "lat", "lon"]], pd.DataFrame(new)], axis=1)


def feature_columns() -> list[str]:
    cols = [f"pm25_si_lag{k}" for k in SI_LAGS]
    cols += [f"{p}_lag{k}" for p in POLLUTANTS.values() for k in POLLUTANT_LAGS]
    cols += ["pm25_si_roll7", "pm25_si_roll14"]
    cols += [c for w in WEATHER for c in (w, f"{w}_lag1")]
    cols += ["doy_sin", "doy_cos", "month", "weekday", "lat", "lon"]
    return cols


TARGETS = [f"pm25_si_t+{h}" for h in HORIZONS]


def assign_split(dates: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=dates.index, dtype="object")
    for name, (lo, hi) in SPLITS.items():
        out[(dates >= lo) & (dates <= hi)] = name
    return out


# ---------------------------------------------------------------- baselines
BASELINE_COLUMNS = {
    "persistence": lambda h: "pm25_si_lag0",
    "seasonal_naive": lambda h: f"pm25_si_lag{7 - h}",
}


def _err(part: pd.DataFrame, name: str, h: int) -> np.ndarray:
    pred = part[BASELINE_COLUMNS[name](h)].to_numpy(float)
    return pred - part[f"pm25_si_t+{h}"].to_numpy(float)


def baselines(df: pd.DataFrame) -> dict:
    """MAE/RMSE per split, baseline and horizon; test MAE per season (season of the target day)."""
    res: dict = {}
    for split, part in df.groupby("split"):
        res[split] = {}
        for name in BASELINE_COLUMNS:
            for h in HORIZONS:
                e = _err(part, name, h)
                res[split].setdefault(name, {})[f"h{h}"] = {
                    "mae": round(float(np.mean(np.abs(e))), 3),
                    "rmse": round(float(np.sqrt(np.mean(e**2))), 3),
                }
    test = df[df["split"] == "test"]
    by_season: dict = {}
    for h in HORIZONS:
        target_month = (pd.to_datetime(test["date"]) + pd.Timedelta(days=h)).dt.month
        for season, part in test.groupby(target_month.map(SEASONS)):
            for name in BASELINE_COLUMNS:
                by_season.setdefault(name, {}).setdefault(f"h{h}", {})[season] = {
                    "n": int(len(part)),
                    "mae": round(float(np.mean(np.abs(_err(part, name, h)))), 3),
                }
    res["test_by_season"] = by_season
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
    invalidated = {"negative": 0, "pm10_ceiling": 0}
    for f in files:
        rid = int(f.name.split(".")[0])
        hourly, counts = read_cams(f)
        for k, v in counts.items():
            invalidated[k] += v
        d = daily_table(hourly)
        d.index.name = "date"
        d = d.reset_index()
        d.insert(0, "region_id", rid)
        daily_frames.append(d)
    daily = pd.concat(daily_frames, ignore_index=True)

    started = daily[daily[[f"{p}_mean" for p in POLLUTANTS.values()]].notna().any(axis=1)]
    day_stats = {
        "region_days_with_any_data": int(len(started)),
        "region_days_valid_pm25_si": int(started["pm25_si"].notna().sum()),
        "pollutant_days_below_16h": {
            p: int(started[f"{p}_mean"].isna().sum()) for p in POLLUTANTS.values()
        },
        "invalidated_hourly_values": invalidated,
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
        "target_missing": TARGETS,
        "pm25_si_lag_missing": [f"pm25_si_lag{k}" for k in SI_LAGS],
        "pm25_si_rolling_missing": ["pm25_si_roll7", "pm25_si_roll14"],
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
    for c in [f"pm25_si_lag{k}" for k in SI_LAGS] + TARGETS:
        out[c] = out[c].astype("int16")
    out = out[["region_id", "date", "split", *fcols, *TARGETS]].reset_index(drop=True)

    report = {
        "target": "CPCB PM2.5 sub-index of the daily 24-h mean CAMS PM2.5 (>= 16 valid hours)",
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
                "target_h1_min": int(x["pm25_si_t+1"].min()),
                "target_h1_max": int(x["pm25_si_t+1"].max()),
                "target_h1_mean": round(float(x["pm25_si_t+1"].mean()), 2),
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
