"""Download hourly CAMS air-quality history per district centroid from Open-Meteo.

Same source and variables the live API ingests (app/providers/open_meteo_air.py), so a model
trained on this data sees the same inputs in production. CAMS global history on Open-Meteo starts
2022-08-01; earlier dates come back as nulls.

Open-Meteo free tier counts a request covering more than two weeks as several calls
(~85 calls for 3+ years of one location) with limits of 600/minute, 5,000/hour and 10,000/day
per IP. The script therefore:
  * downloads one district per request, the full date range at once;
  * visits districts in a state-stratified order (round-robin over states, seeded shuffle inside
    each state), so any prefix of the run is a geographically spread sample;
  * skips districts already on disk (resumable) and stops cleanly on an hourly/daily 429.

Output: one gzip CSV per district, <out-dir>/<region_id>.csv.gz with columns
time (Asia/Kolkata), pm2_5, pm10, nitrogen_dioxide, sulphur_dioxide, carbon_monoxide, ozone.
Missing hours stay empty; nothing is filled in.

    python ml/pipeline/download_air_history.py --regions regions_centroids.csv \
        --start 2022-08-01 --end 2026-10-31 --out-dir data/raw/cams --max-districts 55
"""

import argparse
import csv
import gzip
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
VARIABLES = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "carbon_monoxide",
    "ozone",
]


def stratified_order(regions: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    by_state: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in regions:
        by_state[r["state"]].append(r)
    queues = []
    for state in sorted(by_state):
        items = sorted(by_state[state], key=lambda r: int(r["region_id"]))
        rng.shuffle(items)
        queues.append(items)
    ordered: list[dict[str, str]] = []
    while any(queues):
        for q in queues:
            if q:
                ordered.append(q.pop(0))
    return ordered


def fetch(client: httpx.Client, lat: str, lon: str, start: str, end: str) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(VARIABLES),
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
            return resp.json()
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


def write_csv(path: Path, hourly: dict) -> int:
    times = hourly.get("time", [])
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time", *VARIABLES])
        for i, t in enumerate(times):
            row = [t]
            for v in VARIABLES:
                series = hourly.get(v) or []
                val = series[i] if i < len(series) else None
                row.append("" if val is None else val)
            w.writerow(row)
    tmp.rename(path)
    return len(times)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--regions", type=Path, required=True, help="CSV: region_id,district,state,lat,lon")
    p.add_argument("--start", default="2022-08-01")
    p.add_argument("--end", required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/raw/cams"))
    p.add_argument("--max-districts", type=int, default=55, help="new districts this run")
    p.add_argument("--pause", type=float, default=12.0, help="seconds between requests")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    with args.regions.open() as fh:
        regions = list(csv.DictReader(fh))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    done = 0
    with httpx.Client() as client:
        for r in stratified_order(regions, args.seed):
            out = args.out_dir / f"{r['region_id']}.csv.gz"
            if out.exists():
                continue
            if done >= args.max_districts:
                break
            print(f"{r['region_id']} {r['district']} ({r['state']})", flush=True)
            data = fetch(client, r["lat"], r["lon"], args.start, args.end)
            if data is None:
                print(f"stopped after {done} new districts", flush=True)
                return 2
            n = write_csv(out, data.get("hourly", {}))
            done += 1
            print(f"  {n} hours saved", flush=True)
            time.sleep(args.pause)

    total = len(list(args.out_dir.glob("*.csv.gz")))
    print(f"done: {done} new districts this run, {total}/{len(regions)} on disk", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
