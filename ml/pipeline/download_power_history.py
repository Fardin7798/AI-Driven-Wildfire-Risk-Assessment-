"""Download daily historical weather per district centroid from NASA POWER (no API key).

Why NASA POWER for training: Open-Meteo's free tier (10k weighted calls/day) cannot serve
~676 districts x multiple years of daily archive data. NASA POWER returns a full multi-year
daily series per point in one request. Variables are restricted to the ones the live
Open-Meteo provider also returns, so the model only uses features available at inference:

    T2M_MAX      -> temp_max   (deg C)
    T2M          -> temp_mean  (deg C)
    RH2M         -> rh_mean    (%)
    WS10M_MAX    -> wind_max   (converted m/s -> km/h, Open-Meteo unit)
    PRECTOTCORR  -> precip_sum (mm/day)

Output: <out-dir>/power_daily.parquet with columns
    gadm_id, date, temp_max, temp_mean, rh_mean, wind_max, precip_sum
Per-district JSON responses are cached in <out-dir>/_cache (resumable).
Missing values (-999) are kept as NaN, never filled.
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
import pandas as pd

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = ["T2M_MAX", "T2M", "RH2M", "WS10M_MAX", "PRECTOTCORR"]
RENAME = {
    "T2M_MAX": "temp_max",
    "T2M": "temp_mean",
    "RH2M": "rh_mean",
    "WS10M_MAX": "wind_max",
    "PRECTOTCORR": "precip_sum",
}


def fetch_point(lat: float, lon: float, start: date, end: date) -> dict:
    params = {
        "parameters": ",".join(PARAMS),
        "community": "AG",
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    for attempt in range(5):
        try:
            r = httpx.get(POWER_URL, params=params, timeout=180.0)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            time.sleep(10 * (attempt + 1))
            last = exc
    raise RuntimeError(f"NASA POWER failed for {lat},{lon}: {last}")


def to_frame(gadm_id: str, payload: dict) -> pd.DataFrame:
    p = payload["properties"]["parameter"]
    days = sorted(p[PARAMS[0]].keys())
    df = pd.DataFrame({"date": pd.to_datetime(days, format="%Y%m%d").date})
    for k in PARAMS:
        vals = np.array([p[k].get(d, -999.0) for d in days], dtype=float)
        vals[vals <= -998] = np.nan
        df[RENAME[k]] = vals
    df["wind_max"] = df["wind_max"] * 3.6  # m/s -> km/h
    df.insert(0, "gadm_id", gadm_id)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--gadm", type=Path, required=True, help="GADM 4.1 level-2 GeoJSON")
    ap.add_argument("--start", type=date.fromisoformat, default=date(2018, 9, 1))
    ap.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    ap.add_argument("--out-dir", type=Path, default=Path("data/raw/power"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cache = args.out_dir / "_cache"
    cache.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(args.gadm)
    # Same centroid definition as wf.regions (ST_Centroid of the district polygon)
    cent = gdf.geometry.centroid
    jobs = [
        (row.GID_2, float(c.y), float(c.x)) for row, c in zip(gdf.itertuples(), cent, strict=True)
    ]

    def work(job: tuple[str, float, float]) -> str:
        gid, lat, lon = job
        f = cache / f"{gid}.json"
        if not f.exists():
            f.write_text(json.dumps(fetch_point(lat, lon, args.start, args.end)))
        return gid

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for fut in as_completed([ex.submit(work, j) for j in jobs]):
            fut.result()
            done += 1
            if done % 50 == 0:
                print(f"{done}/{len(jobs)} districts", flush=True)

    frames = [to_frame(gid, json.loads((cache / f"{gid}.json").read_text())) for gid, _, _ in jobs]
    out = pd.concat(frames, ignore_index=True)
    out_file = args.out_dir / "power_daily.parquet"
    out.to_parquet(out_file, index=False)
    print(f"wrote {len(out):,} rows for {len(jobs)} districts -> {out_file}")


if __name__ == "__main__":
    main()
