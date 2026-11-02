"""Build the station x day PM2.5 forecasting table. Target: CPCB PM2.5 sub-index measured at a
CPCB station (OpenAQ v3 daily PM2.5), at t+1, t+2, t+3.

Stations
  * CPCB/caaqm PM2.5 sensors whose GADM level-2 district has a CAMS file.
  * OpenAQ lists one physical monitor under several ids (a CPCB and a caaqm copy, or an old and
    a new sensor id). Locations within STATION_RADIUS_M of each other are merged into one station
    (single-linkage), so a monitor is never counted twice. On a day where more than one cleaned
    sensor value exists for a station, the station value is their mean; how many such days there
    were, and how many had identical values (duplicates), is reported.
  * Station days are cleaned with `aqi_sources.clean_station_days` (no imputation).

Rows: one per (station, day t) inside a split with at least one target present. Features use
only days <= t; missing inputs stay NaN (XGBoost handles them); nothing is filled.
  st_*     station: sub-index lags 0-6, trailing 7/14/30-day means (>= 5/10/20 valid days),
           valid-day count in the last 7 days, station PM10 lags 0-2 (same cleaning)
  bias_*   station minus CAMS sub-index (lag0, 7-day mean)
  cams_*   district CAMS: PM2.5 sub-index lags 0-6 and 7/14-day means (>= 5/10 valid days),
           24-h means of PM2.5/PM10/NO2/SO2/CO/O3 lags 0-2 (>= 16 valid hours)
  weather  NASA POWER district weather of day t and t-1
  calendar doy_sin, doy_cos, month, weekday; static: station lat, lon
Lags are calendar lags (a missing day is missing, never the previous row).
Targets: pm25_si_t+{1,2,3} (station). Reference column (never a feature): ref_cams_si_t+{h},
the CAMS district sub-index on the target day, for the "raw CAMS" comparison only.
Split column from aqi_sources.SPLITS (by day t).

Outputs (gitignored): <out-dir>/aqi_station_dataset.parquet, stations.csv, build_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aqi_sources import (  # noqa: E402
    EXCLUSION_RULES,
    POLLUTANTS,
    WEATHER,
    assign_split,
    clean_station_days,
    daily_table,
    match_sensors,
    pm25_sub_index,
    read_cams,
    region_gadm_map,
)

STATION_RADIUS_M = 300.0
HORIZONS = (1, 2, 3)
SI_LAGS = range(7)
POLLUTANT_LAGS = range(3)
ST_ROLL = {7: 5, 14: 10, 30: 20}  # window: minimum valid days
CAMS_ROLL = {7: 5, 14: 10}
TARGETS = [f"pm25_si_t+{h}" for h in HORIZONS]
REFERENCE = [f"ref_cams_si_t+{h}" for h in HORIZONS]
ID_COLS = ["station_id", "region_id", "date", "split"]


# ---------------------------------------------------------------- stations
def cluster_locations(locs: pd.DataFrame, radius_m: float = STATION_RADIUS_M) -> pd.Series:
    """location_id -> station_id (smallest location_id of its single-linkage cluster)."""
    locs = locs.drop_duplicates("location_id").reset_index(drop=True)
    lat = np.radians(locs["lat"].to_numpy(float))
    lon = np.radians(locs["lon"].to_numpy(float))
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    near = 2 * 6_371_000 * np.arcsin(np.sqrt(np.clip(a, 0, 1))) <= radius_m
    parent = list(range(len(locs)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in zip(*np.nonzero(near), strict=True):
        ri, rj = find(int(i)), find(int(j))
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    ids = locs["location_id"].to_numpy()
    roots = [find(i) for i in range(len(locs))]
    root_min = pd.Series(ids).groupby(roots).transform("min").to_numpy()
    return pd.Series(root_min, index=ids, name="station_id")


def station_daily(days: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Cleaned sensor days (station_id, parameter, date, value) -> one value per station,
    parameter and day (mean of sensors), plus counts of multi-sensor days."""
    g = days.groupby(["station_id", "parameter", "date"])["value"]
    out = g.agg(value="mean", n="size", spread=lambda v: float(v.max() - v.min())).reset_index()
    multi = out[out["n"] > 1]
    stats = {
        p: {
            "station_days": int((out["parameter"] == p).sum()),
            "days_with_several_sensor_values": int((multi["parameter"] == p).sum()),
            "of_which_identical_values": int(
                ((multi["parameter"] == p) & (multi["spread"] < 0.05)).sum()
            ),
        }
        for p in ("pm25", "pm10")
    }
    return out[["station_id", "parameter", "date", "value"]], stats


def calendar_panel(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Reindex each `key` group to every calendar day between its first and last date."""
    parts = []
    for k, part in df.groupby(key, sort=True):
        days = pd.date_range(min(part["date"]), max(part["date"]), freq="D").date
        full = pd.DataFrame({key: k, "date": days})
        parts.append(full.merge(part, on=[key, "date"], how="left"))
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------- features
def _roll(g, col: str, w: int, min_n: int) -> pd.Series:
    return g[col].transform(lambda s: s.rolling(w, min_periods=min_n).mean())


def district_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Calendar-complete district panel (region_id, date, <p>_mean, pm25_si, weather) ->
    district features at day t, plus reference CAMS sub-index on t+h (not a feature)."""
    p = panel.sort_values(["region_id", "date"]).reset_index(drop=True)
    g = p.groupby("region_id", sort=False)
    new: dict[str, pd.Series] = {}
    for k in SI_LAGS:
        new[f"cams_pm25_si_lag{k}"] = g["pm25_si"].shift(k)
    for w, n in CAMS_ROLL.items():
        new[f"cams_pm25_si_roll{w}"] = _roll(g, "pm25_si", w, n)
    for pol in POLLUTANTS.values():
        for k in POLLUTANT_LAGS:
            new[f"cams_{pol}_lag{k}"] = g[f"{pol}_mean"].shift(k)
    for col in WEATHER:
        new[col] = p[col]
        new[f"{col}_lag1"] = g[col].shift(1)
    for h in HORIZONS:
        new[f"ref_cams_si_t+{h}"] = g["pm25_si"].shift(-h)
    return pd.concat([p[["region_id", "date"]], pd.DataFrame(new)], axis=1)


def station_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Calendar-complete station panel (station_id, date, st_si, st_pm10) -> station features at
    day t and targets at t+h."""
    p = panel.sort_values(["station_id", "date"]).reset_index(drop=True)
    g = p.groupby("station_id", sort=False)
    new: dict[str, pd.Series] = {}
    for k in SI_LAGS:
        new[f"st_si_lag{k}"] = g["st_si"].shift(k)
    for w, n in ST_ROLL.items():
        new[f"st_si_roll{w}"] = _roll(g, "st_si", w, n)
    new["st_nvalid7"] = g["st_si"].transform(lambda s: s.notna().rolling(7, min_periods=1).sum())
    for k in POLLUTANT_LAGS:
        new[f"st_pm10_lag{k}"] = g["st_pm10"].shift(k)
    for h in HORIZONS:
        new[f"pm25_si_t+{h}"] = g["st_si"].shift(-h)
    return pd.concat([p[["station_id", "date"]], pd.DataFrame(new)], axis=1)


def combine(st: pd.DataFrame, dist: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Join station and district features on (district of the station, day t); add bias,
    calendar and static columns."""
    meta = stations.set_index("station_id")
    st = st.assign(region_id=st["station_id"].map(meta["region_id"]).astype(int))
    df = st.merge(dist, on=["region_id", "date"], how="left")
    df["bias_si_lag0"] = df["st_si_lag0"] - df["cams_pm25_si_lag0"]
    df["bias_si_roll7"] = df["st_si_roll7"] - df["cams_pm25_si_roll7"]
    dt = pd.to_datetime(df["date"])
    doy = dt.dt.day_of_year.astype(float)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["month"] = dt.dt.month
    df["weekday"] = dt.dt.day_of_week
    df["lat"] = df["station_id"].map(meta["lat"])
    df["lon"] = df["station_id"].map(meta["lon"])
    return df


def feature_columns(df: pd.DataFrame) -> list[str]:
    skip = set(ID_COLS) | set(TARGETS) | set(REFERENCE)
    return [c for c in df.columns if c not in skip]


def station_feature(col: str) -> bool:
    """True for features that need a live station (excluded from the no-station model)."""
    return col.startswith(("st_", "bias_"))


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--cams", type=Path, default=Path("data/raw/cams"))
    ap.add_argument("--openaq", type=Path, default=Path("data/raw/openaq"))
    ap.add_argument("--power", type=Path, default=Path("data/raw/power_aqi/power_daily.parquet"))
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("data/processed/aqi_station"))
    args = ap.parse_args()

    regions = pd.read_csv(args.regions)
    gmap = region_gadm_map(regions, args.gadm)
    rids = {int(f.name.split(".")[0]) for f in args.cams.glob("*.csv.gz")}
    if not rids:
        raise SystemExit(f"no CAMS files in {args.cams}")

    # --- sensors -> districts -> stations
    sensors = pd.read_csv(args.openaq / "sensors.csv")
    sensors = sensors[sensors["parameter"].isin(["pm25", "pm10"])].copy()
    sensors["region_id"] = match_sensors(sensors, json.loads(args.gadm.read_text()), regions, rids)
    if (sensors["region_id"] == -1).any():
        raise ValueError("a sensor falls in more than one district polygon")
    sensors = sensors[sensors["region_id"].notna()].copy()
    sensors["region_id"] = sensors["region_id"].astype(int)
    pm25_locs = sensors.loc[sensors["parameter"] == "pm25", "location_id"].unique()
    locs = sensors[sensors["location_id"].isin(pm25_locs)]
    loc2st = cluster_locations(locs[["location_id", "lat", "lon"]])
    sensors = sensors[sensors["location_id"].isin(loc2st.index)].copy()
    sensors["station_id"] = sensors["location_id"].map(loc2st)
    if (sensors.groupby("station_id")["region_id"].nunique() > 1).any():
        raise ValueError("a merged station spans two districts")

    # --- clean sensor days
    excluded = dict.fromkeys(EXCLUSION_RULES, 0)
    raw_days = {"pm25": 0, "pm10": 0}
    kept = []
    for s in sensors.itertuples():
        f = args.openaq / "sensors" / f"{s.sensor_id}.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f)
        if d.empty:
            continue
        raw_days[s.parameter] += len(d)
        d, counts = clean_station_days(d)
        if s.parameter == "pm25":
            for k, v in counts.items():
                excluded[k] += v
        kept.append(
            pd.DataFrame(
                {
                    "station_id": s.station_id,
                    "parameter": s.parameter,
                    "date": pd.to_datetime(d["date"]).dt.date,
                    "value": d["value"].astype(float),
                }
            )
        )
    sdays, multi = station_daily(pd.concat(kept, ignore_index=True))
    pm25 = sdays[sdays["parameter"] == "pm25"].rename(columns={"value": "st_pm25"})
    pm10 = sdays[sdays["parameter"] == "pm10"].rename(columns={"value": "st_pm10"})
    spanel = calendar_panel(pm25.drop(columns="parameter"), "station_id")
    spanel = spanel.merge(pm10.drop(columns="parameter"), on=["station_id", "date"], how="left")
    spanel["st_si"] = pm25_sub_index(spanel["st_pm25"])

    st_meta = (
        sensors[sensors["station_id"].isin(spanel["station_id"].unique())]
        .groupby("station_id")
        .agg(
            region_id=("region_id", "first"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
            name=("location", "first"),
            location_ids=("location_id", lambda v: " ".join(map(str, sorted(set(v))))),
            n_pm25_sensors=("parameter", lambda v: int((v == "pm25").sum())),
        )
        .reset_index()
    )

    # --- district panel: CAMS daily + POWER
    frames = []
    for rid in sorted(st_meta["region_id"].unique()):
        hourly, _ = read_cams(args.cams / f"{rid}.csv.gz")
        d = daily_table(hourly)
        d.index.name = "date"
        frames.append(d.reset_index().assign(region_id=int(rid)))
    dpanel = pd.concat(frames, ignore_index=True)
    power = pd.read_parquet(args.power)
    power["date"] = pd.to_datetime(power["date"]).dt.date
    inv = {v: k for k, v in gmap.items()}
    power = power[power["gadm_id"].isin({gmap[r] for r in dpanel["region_id"].unique()})].copy()
    power["region_id"] = power.pop("gadm_id").map(inv)
    dpanel = dpanel.merge(power, on=["region_id", "date"], how="left")

    df = combine(station_features(spanel), district_features(dpanel), st_meta)
    df["split"] = assign_split(df["date"])
    candidates = df[df["split"].notna()]
    out = candidates[candidates[TARGETS].notna().any(axis=1)].copy()
    fcols = feature_columns(out)
    out = out[[*ID_COLS, *fcols, *TARGETS, *REFERENCE]].reset_index(drop=True)

    report = {
        "target": "CPCB PM2.5 sub-index of cleaned CPCB station daily PM2.5 (OpenAQ v3), t+1..t+3",
        "station_radius_m": STATION_RADIUS_M,
        "pm25_sensors_in_cams_districts": int((sensors["parameter"] == "pm25").sum()),
        "pm25_locations": int(len(loc2st)),
        "stations_after_merging": int(loc2st.nunique()),
        "stations_with_kept_pm25_days": int(spanel["station_id"].nunique()),
        "raw_sensor_days": raw_days,
        "pm25_sensor_days_excluded_by_rule": excluded,
        "station_days": multi,
        "rows": {
            "station_days_in_splits": int(len(candidates)),
            "kept_any_target": int(len(out)),
            **{f"with_target_h{h}": int(out[f"pm25_si_t+{h}"].notna().sum()) for h in HORIZONS},
        },
        "splits": {
            s: {
                "rows": int(len(x)),
                "stations": int(x["station_id"].nunique()),
                "districts": int(x["region_id"].nunique()),
                "date_min": str(x["date"].min()),
                "date_max": str(x["date"].max()),
                "target_h1_n": int(x["pm25_si_t+1"].notna().sum()),
                "target_h1_mean": round(float(x["pm25_si_t+1"].mean()), 2),
                "persistence_available_h1": int(
                    (x["pm25_si_t+1"].notna() & x["st_si_lag0"].notna()).sum()
                ),
            }
            for s, x in out.groupby("split")
        },
        "feature_missing_share": {
            c: round(float(out[c].isna().mean()), 4) for c in fcols if out[c].isna().any()
        },
        "n_features": len(fcols),
        "n_no_station_features": sum(not station_feature(c) for c in fcols),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out_dir / "aqi_station_dataset.parquet", index=False)
    st_meta.to_csv(args.out_dir / "stations.csv", index=False)
    (args.out_dir / "build_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "feature_missing_share"}, indent=2))


if __name__ == "__main__":
    main()
