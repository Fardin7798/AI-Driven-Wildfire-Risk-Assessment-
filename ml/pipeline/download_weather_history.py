"""Download daily weather history per district centroid from the Open-Meteo Historical Forecast API.

Why this source: the live forecaster will read the same daily values from the Open-Meteo Forecast
API (`past_days`), which serves yesterday's weather without delay. The Historical Forecast API
archives exactly those values (the first hours of each model run, stitched; default "best match"
model), so training and serving see identical numbers. Checked with real requests on 2026-11-02:
8 districts x 92 past days x 5 variables, Forecast API past_days == Historical Forecast API,
max abs diff 0.0. ERA5 (Historical Weather API) is a different dataset and is not used.

Request: district centroid (regions_centroids.csv lat/lon), timezone=Asia/Kolkata, daily
aggregates of IST calendar days, default units (deg C, %, km/h, mm).

    temperature_2m_max        -> temp_max
    temperature_2m_mean       -> temp_mean
    relative_humidity_2m_mean -> rh_mean
    wind_speed_10m_max        -> wind_max  (km/h)
    precipitation_sum         -> precip_sum

Output: one CSV per district, <out-dir>/<region_id>.csv (date + the five columns above; a day
the API returns as null stays empty, nothing is filled) and <out-dir>/grid.csv (the model grid
point Open-Meteo used for each centroid). Resumable; stops cleanly on an hourly/daily 429.

    python ml/pipeline/download_weather_history.py --regions regions_centroids.csv \
        --region-ids 5,6,16 --start 2022-07-25 --end 2026-10-28 --out-dir data/raw/openmeteo_weather
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import httpx

URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
DAILY = {
    "temperature_2m_max": "temp_max",
    "temperature_2m_mean": "temp_mean",
    "relative_humidity_2m_mean": "rh_mean",
    "wind_speed_10m_max": "wind_max",
    "precipitation_sum": "precip_sum",
}


def fetch(client: httpx.Client, lat: str, lon: str, start: str, end: str) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DAILY),
        "start_date": start,
        "end_date": end,
        "timezone": "Asia/Kolkata",
    }
    for attempt in range(1, 4):
        try:
            resp = client.get(URL, params=params, timeout=120.0)
        except httpx.RequestError as e:
            print(f"  network error ({e}); retry {attempt}/3", flush=True)
            time.sleep(10 * attempt)
            continue
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                print(f"  invalid JSON body; retry {attempt}/3", flush=True)
                time.sleep(10 * attempt)
                continue
        if resp.status_code == 429:
            reason = resp.text[:200]
            if "hourly" in reason.lower() or "daily" in reason.lower():
                print(f"  quota exhausted, stopping: {reason}", flush=True)
                return None
            print(f"  minutely limit, waiting 61 s: {reason}", flush=True)
            time.sleep(61)
            continue
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}", flush=True)
        time.sleep(10 * attempt)
    return None


def write_csv(path: Path, daily: dict) -> int:
    days = daily.get("time", [])
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", *DAILY.values()])
        for i, d in enumerate(days):
            row = [d]
            for v in DAILY:
                series = daily.get(v) or []
                val = series[i] if i < len(series) else None
                row.append("" if val is None else val)
            w.writerow(row)
    tmp.rename(path)
    return len(days)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--regions", type=Path, required=True, help="CSV: region_id,lat,lon,...")
    p.add_argument("--region-ids", required=True, help="comma-separated region_ids to download")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/raw/openmeteo_weather"))
    p.add_argument("--pause", type=float, default=2.0, help="seconds between requests")
    args = p.parse_args()

    wanted = {int(x) for x in args.region_ids.split(",") if x}
    with args.regions.open() as fh:
        regions = [r for r in csv.DictReader(fh) if int(r["region_id"]) in wanted]
    missing = wanted - {int(r["region_id"]) for r in regions}
    if missing:
        raise SystemExit(f"region_ids not in {args.regions}: {sorted(missing)}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    grid_path = args.out_dir / "grid.csv"
    new_grid = not grid_path.exists()

    done = 0
    with httpx.Client() as client, grid_path.open("a", newline="") as gfh:
        gw = csv.writer(gfh)
        if new_grid:
            gw.writerow(["region_id", "lat", "lon", "grid_lat", "grid_lon", "grid_elevation"])
        for r in sorted(regions, key=lambda r: int(r["region_id"])):
            out = args.out_dir / f"{r['region_id']}.csv"
            if out.exists():
                continue
            print(f"{r['region_id']} {r['district']} ({r['state']})", flush=True)
            data = fetch(client, r["lat"], r["lon"], args.start, args.end)
            if data is None:
                print(f"stopped after {done} new districts", flush=True)
                return 2
            n = write_csv(out, data.get("daily", {}))
            gw.writerow(
                [
                    r["region_id"],
                    r["lat"],
                    r["lon"],
                    data.get("latitude"),
                    data.get("longitude"),
                    data.get("elevation"),
                ]
            )
            gfh.flush()
            done += 1
            print(f"  {n} days saved", flush=True)
            time.sleep(args.pause)

    total = len(list(args.out_dir.glob("[0-9]*.csv")))
    print(f"done: {done} new districts this run, {total}/{len(wanted)} on disk", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
