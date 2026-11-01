"""Validate CAMS district PM2.5/PM10 against CPCB station daily means (OpenAQ v3).

For every CPCB/caaqm PM sensor in data/raw/openaq/sensors.csv, find the district (among the
districts that have a CAMS file) whose GADM 4.1 level-2 polygon contains the station, then pair
the station's daily value with the CAMS daily 24-h mean of that district on the same date.

Rules (nothing is filled or imputed):
  * Station day kept only when OpenAQ pct_complete >= 75 (and a value is present).
  * CAMS day is the 24-h mean with >= 16 valid hours (build_aqi_dataset.daily_mean_24h).
  * Both sides are Asia/Kolkata calendar days (CAMS downloaded with timezone=Asia/Kolkata,
    OpenAQ daily periods taken from their local date).
  * region_id = GADM feature index + 1; regions CSV names are checked against GADM.
  * Pairs are per sensor-day (a district with several stations contributes several pairs).
  * Sensitivity ("overall_station_qc"): additionally drops station days that look like
    instrument artefacts: value <= 0, value >= 985 (CPCB analyser ceiling, 985 recurs exactly),
    pct_complete > 100, and runs of >= 5 identical consecutive daily values (stuck sensor).
    The primary numbers keep them, exactly as the pct_complete >= 75 rule specifies.

Reported for PM2.5 and PM10, overall and by Indian season (winter DJF, pre-monsoon MAM,
monsoon JJAS, post-monsoon ON): n pairs, n sensors, n districts, bias (mean CAMS - station),
MAE, Pearson r, plus medians of both sides.

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
from build_aqi_dataset import daily_mean_24h, read_cams

MIN_PCT_COMPLETE = 75.0
STUCK_RUN_DAYS = 5
STATION_CEILING = 985.0
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


def stats(df: pd.DataFrame) -> dict:
    c, s = df["cams"].to_numpy(float), df["station"].to_numpy(float)
    out: dict = {
        "n_pairs": len(df),
        "n_sensors": int(df["sensor_id"].nunique()),
        "n_districts": int(df["region_id"].nunique()),
    }
    if len(df) < 2:
        return out
    e = c - s
    out.update(
        {
            "bias": round(float(e.mean()), 2),
            "mae": round(float(np.abs(e).mean()), 2),
            "pearson_r": round(float(np.corrcoef(c, s)[0, 1]), 3),
            "cams_median": round(float(np.median(c)), 2),
            "station_median": round(float(np.median(s)), 2),
        }
    )
    return out


def stuck_mask(d: pd.DataFrame) -> pd.Series:
    """True for days inside a run of >= STUCK_RUN_DAYS identical values on consecutive dates."""
    dt = pd.to_datetime(d["date"])
    brk = (d["value"] != d["value"].shift()) | (dt.diff() != pd.Timedelta(days=1))
    run = brk.cumsum()
    return run.map(run.value_counts()) >= STUCK_RUN_DAYS


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
    sensors["region_id"] = match_sensors(
        sensors, json.loads(args.gadm.read_text()), pd.read_csv(args.regions), rids
    )
    if (sensors["region_id"] == -1).any():
        raise ValueError("a sensor falls in more than one district polygon")
    matched = sensors[sensors["region_id"].notna()].copy()
    matched["region_id"] = matched["region_id"].astype(int)

    cams_daily: dict[int, pd.DataFrame] = {}
    for rid in sorted(matched["region_id"].unique()):
        h = read_cams(args.cams / f"{rid}.csv.gz")
        cams_daily[rid] = pd.DataFrame(
            {"pm25": daily_mean_24h(h["pm25"]), "pm10": daily_mean_24h(h["pm10"])}
        )

    pairs = []
    station_days = {"total": 0, "kept_pct_ge_75": 0, "pct_gt_100": 0, "missing_file": 0}
    for s in matched.itertuples():
        f = args.openaq / "sensors" / f"{s.sensor_id}.csv"
        if not f.exists():
            station_days["missing_file"] += 1
            continue
        d = pd.read_csv(f)
        station_days["total"] += len(d)
        d = d.assign(stuck=stuck_mask(d))  # on the full series, before filtering
        d = d[d["value"].notna() & (d["pct_complete"] >= MIN_PCT_COMPLETE)]
        station_days["kept_pct_ge_75"] += len(d)
        station_days["pct_gt_100"] += int((d["pct_complete"] > 100).sum())
        cd = cams_daily[s.region_id][s.parameter]
        d = d.assign(date=pd.to_datetime(d["date"]).dt.date)
        d["cams"] = d["date"].map(cd)
        d = d[d["cams"].notna()]
        pairs.append(
            pd.DataFrame(
                {
                    "sensor_id": s.sensor_id,
                    "region_id": s.region_id,
                    "parameter": s.parameter,
                    "date": d["date"],
                    "station": d["value"].astype(float),
                    "cams": d["cams"],
                    "pct_complete": d["pct_complete"],
                    "stuck": d["stuck"],
                }
            )
        )
    p = pd.concat(pairs, ignore_index=True)
    p["season"] = pd.to_datetime(p["date"]).dt.month.map(SEASONS)

    res: dict = {}
    for par, g in p.groupby("parameter"):
        res[par] = {
            "overall": stats(g),
            "overall_station_qc": stats(
                g[
                    (g["station"] > 0)
                    & (g["station"] < STATION_CEILING)
                    & (g["pct_complete"] <= 100)
                    & ~g["stuck"]
                ]
            ),
            "by_season": {k: stats(x) for k, x in g.groupby("season")},
        }
    report = {
        "rule": "station days pct_complete>=75; CAMS 24h mean >=16 valid h; same IST date",
        "n_cams_districts": len(rids),
        "sensors_total": len(sensors),
        "sensors_in_cams_districts": len(matched),
        "districts_with_sensor": int(matched["region_id"].nunique()),
        "station_days": station_days,
        "date_range": [str(p["date"].min()), str(p["date"].max())],
        "results": res,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
