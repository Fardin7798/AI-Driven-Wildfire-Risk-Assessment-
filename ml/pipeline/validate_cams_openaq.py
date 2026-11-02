"""Validate the CAMS PM2.5 sub-index target against CPCB station PM2.5 sub-indices (OpenAQ v3).

For every CPCB/caaqm PM2.5 sensor in data/raw/openaq/sensors.csv, find the district (among the
districts that have a CAMS file) whose GADM 4.1 level-2 polygon contains the station, then pair
the station's daily PM2.5 with the CAMS daily 24-h mean of that district on the same date. Both
sides are turned into the CPCB PM2.5 sub-index with `app.domain.aqi.calculate_sub_index`.

Rules (nothing is filled or imputed):
  * CAMS day: 24-h mean with >= 16 valid hours, invalid hours dropped
    (build_aqi_dataset.read_cams / daily_mean_24h), i.e. exactly the training target.
  * Station day excluded when: value missing, pct_complete < 75, value <= 0, value == 985
    (CPCB analyser ceiling, recurs exactly), value > 999, or the day is inside a run of >= 5
    identical consecutive daily values (stuck sensor; runs found on the full series).
  * Both sides are Asia/Kolkata calendar days (CAMS downloaded with timezone=Asia/Kolkata,
    OpenAQ daily periods taken from their local date).
  * region_id = GADM feature index + 1; regions CSV names are checked against GADM.
  * Pairs are per sensor-day (a district with several stations contributes several pairs).

Reported overall and by Indian season (season map from build_aqi_dataset): n pairs, n sensors,
n districts, bias (mean CAMS - station), MAE, Pearson r and medians, for the sub-index and for
the raw µg/m³ concentration.

Output: <out> JSON (default data/processed/aqi/cams_validation.json, gitignored).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_aqi_dataset import SEASONS, daily_mean_24h, pm25_sub_index, read_cams

MIN_PCT_COMPLETE = 75.0
STUCK_RUN_DAYS = 5
STATION_CEILING = 985.0
STATION_MAX = 999.0


def stats(cams: np.ndarray, station: np.ndarray) -> dict:
    out: dict = {"n_pairs": len(cams)}
    if len(cams) < 2:
        return out
    e = cams - station
    out.update(
        {
            "bias": round(float(e.mean()), 2),
            "mae": round(float(np.abs(e).mean()), 2),
            "pearson_r": round(float(np.corrcoef(cams, station)[0, 1]), 3),
            "cams_median": round(float(np.median(cams)), 2),
            "station_median": round(float(np.median(station)), 2),
        }
    )
    return out


def group_stats(df: pd.DataFrame) -> dict:
    return {
        "n_sensors": int(df["sensor_id"].nunique()),
        "n_districts": int(df["region_id"].nunique()),
        "sub_index": stats(df["cams_si"].to_numpy(float), df["station_si"].to_numpy(float)),
        "concentration_ug_m3": stats(df["cams"].to_numpy(float), df["station"].to_numpy(float)),
    }


def stuck_mask(d: pd.DataFrame) -> pd.Series:
    """True for days inside a run of >= STUCK_RUN_DAYS identical values on consecutive dates."""
    dt = pd.to_datetime(d["date"])
    brk = (d["value"] != d["value"].shift()) | (dt.diff() != pd.Timedelta(days=1))
    run = brk.cumsum()
    return run.map(run.value_counts()) >= STUCK_RUN_DAYS


def station_exclusions(d: pd.DataFrame) -> dict[str, pd.Series]:
    """Named exclusion masks for one sensor's daily series (each is True = excluded)."""
    v = d["value"]
    return {
        "missing_value": v.isna(),
        "pct_complete_lt_75": ~(d["pct_complete"] >= MIN_PCT_COMPLETE),
        "value_le_0": v <= 0,
        "value_eq_985": v == STATION_CEILING,
        "value_gt_999": v > STATION_MAX,
        "stuck_run_ge_5": stuck_mask(d),
    }


def match_sensors(sensors: pd.DataFrame, gadm: dict, regions: pd.DataFrame, rids: set[int]):
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


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--cams", type=Path, default=Path("data/raw/cams"))
    ap.add_argument("--openaq", type=Path, default=Path("data/raw/openaq"))
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("data/processed/aqi/cams_validation.json"))
    args = ap.parse_args()

    rids = {int(f.name.split(".")[0]) for f in args.cams.glob("*.csv.gz")}
    if not rids:
        raise SystemExit(f"no CAMS files in {args.cams}")
    sensors = pd.read_csv(args.openaq / "sensors.csv")
    sensors = sensors[sensors["parameter"] == "pm25"].copy()
    sensors["region_id"] = match_sensors(
        sensors, json.loads(args.gadm.read_text()), pd.read_csv(args.regions), rids
    )
    if (sensors["region_id"] == -1).any():
        raise ValueError("a sensor falls in more than one district polygon")
    matched = sensors[sensors["region_id"].notna()].copy()
    matched["region_id"] = matched["region_id"].astype(int)

    cams_daily: dict[int, pd.Series] = {}
    for rid in sorted(matched["region_id"].unique()):
        hourly, _ = read_cams(args.cams / f"{rid}.csv.gz")
        cams_daily[rid] = daily_mean_24h(hourly["pm25"])

    pairs = []
    excluded = dict.fromkeys(
        [
            "missing_value",
            "pct_complete_lt_75",
            "value_le_0",
            "value_eq_985",
            "value_gt_999",
            "stuck_run_ge_5",
        ],
        0,
    )
    station_days = {"total": 0, "kept": 0, "missing_file": 0}
    for s in matched.itertuples():
        f = args.openaq / "sensors" / f"{s.sensor_id}.csv"
        if not f.exists():
            station_days["missing_file"] += 1
            continue
        d = pd.read_csv(f)
        station_days["total"] += len(d)
        masks = station_exclusions(d)
        drop = pd.Series(False, index=d.index)
        for name, m in masks.items():
            excluded[name] += int(m.sum())
            drop |= m
        d = d[~drop]
        station_days["kept"] += len(d)
        d = d.assign(date=pd.to_datetime(d["date"]).dt.date)
        d["cams"] = d["date"].map(cams_daily[s.region_id])
        d = d[d["cams"].notna()]
        pairs.append(
            pd.DataFrame(
                {
                    "sensor_id": s.sensor_id,
                    "region_id": s.region_id,
                    "date": d["date"],
                    "station": d["value"].astype(float),
                    "cams": d["cams"],
                }
            )
        )
    p = pd.concat(pairs, ignore_index=True)
    p["station_si"] = pm25_sub_index(p["station"])
    p["cams_si"] = pm25_sub_index(p["cams"])
    p["season"] = pd.to_datetime(p["date"]).dt.month.map(SEASONS)

    report = {
        "rule": (
            "PM2.5 sub-index (CPCB). CAMS 24h mean >=16 valid h; station days excluded if "
            "pct_complete<75, value<=0, ==985, >999, or in a >=5-day identical run; same IST date"
        ),
        "n_cams_districts": len(rids),
        "pm25_sensors_total": len(sensors),
        "pm25_sensors_in_cams_districts": len(matched),
        "districts_with_sensor": int(matched["region_id"].nunique()),
        "station_days": station_days,
        "station_days_excluded_by_rule": excluded,
        "date_range": [str(p["date"].min()), str(p["date"].max())],
        "overall": group_stats(p),
        "by_season": {k: group_stats(x) for k, x in p.groupby("season")},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
