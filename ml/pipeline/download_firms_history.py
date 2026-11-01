"""Download historical NASA FIRMS detections for a country bounding box via the FIRMS Area API.

Uses the standard-processing (SP) archive of one sensor so that training labels and the
live `fires_prev_*` features come from the same instrument (default: VIIRS NOAA-20).

Output: one parquet file per year in --out-dir (resumable: finished years are skipped,
finished 5-day chunks are cached as CSV in <out-dir>/_chunks).

Example:
    FIRMS_MAP_KEY=xxxx python ml/pipeline/download_firms_history.py \
        --source VIIRS_NOAA20_SP --start 2019-01-01 --end 2024-12-31 --out-dir data/raw/firms
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import pandas as pd

FIRMS_AREA_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}/{start}"
)
INDIA_BBOX = "68,6,98,38"  # west,south,east,north
CHUNK_DAYS = 5  # FIRMS Area API maximum day range per request
KEEP_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "confidence",
    "frp",
    "daynight",
    "type",
]


def fetch_chunk(
    client: httpx.Client, key: str, source: str, bbox: str, start: date, days: int
) -> str:
    url = FIRMS_AREA_URL.format(
        key=key, source=source, bbox=bbox, days=days, start=start.isoformat()
    )
    for attempt in range(5):
        try:
            resp = client.get(url, timeout=180.0)
            text = resp.text
            if resp.status_code == 200 and text.startswith("latitude"):
                return text
            if resp.status_code == 200 and not text.strip():
                return ""
            # FIRMS returns plain-text errors with HTTP 200 sometimes (e.g. invalid key / limit)
            raise RuntimeError(f"FIRMS error ({resp.status_code}): {text[:200]}")
        except (httpx.HTTPError, RuntimeError) as exc:
            wait = 15 * (attempt + 1)
            print(
                f"  chunk {start} attempt {attempt + 1} failed: {exc}; retry in {wait}s", flush=True
            )
            time.sleep(wait)
    raise RuntimeError(f"FIRMS chunk {start} failed after retries")


def download(source: str, start: date, end: date, out_dir: Path, bbox: str, key: str) -> None:
    chunk_dir = out_dir / "_chunks" / source
    chunk_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        for year in range(start.year, end.year + 1):
            year_file = out_dir / f"{source}_{year}.parquet"
            if year_file.exists():
                print(f"{year}: already downloaded", flush=True)
                continue
            y_start = max(start, date(year, 1, 1))
            y_end = min(end, date(year, 12, 31))
            frames: list[pd.DataFrame] = []
            cur = y_start
            while cur <= y_end:
                days = min(CHUNK_DAYS, (y_end - cur).days + 1)
                cache = chunk_dir / f"{cur.isoformat()}_{days}.csv"
                if cache.exists():
                    text = cache.read_text()
                else:
                    text = fetch_chunk(client, key, source, bbox, cur, days)
                    cache.write_text(text)
                if text.strip():
                    df = pd.read_csv(io.StringIO(text), low_memory=False)
                    frames.append(df[[c for c in KEEP_COLUMNS if c in df.columns]])
                cur += timedelta(days=days)
            if not frames:
                raise RuntimeError(
                    f"No FIRMS rows returned for {source} {year}; refusing to write empty year"
                )
            year_df = pd.concat(frames, ignore_index=True)
            year_df["acq_date"] = pd.to_datetime(year_df["acq_date"]).dt.date
            year_df.to_parquet(year_file, index=False)
            print(f"{year}: {len(year_df):,} detections -> {year_file}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--source", default="VIIRS_NOAA20_SP")
    p.add_argument("--start", type=date.fromisoformat, default=date(2019, 1, 1))
    p.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    p.add_argument("--bbox", default=INDIA_BBOX)
    p.add_argument("--out-dir", type=Path, default=Path("data/raw/firms"))
    args = p.parse_args()

    key = os.environ.get("FIRMS_MAP_KEY", "")
    if not key:
        sys.exit("FIRMS_MAP_KEY environment variable is required")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    download(args.source, args.start, args.end, args.out_dir, args.bbox, key)


if __name__ == "__main__":
    main()
