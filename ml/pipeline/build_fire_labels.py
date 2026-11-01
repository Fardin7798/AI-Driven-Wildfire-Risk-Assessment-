"""Spatially join FIRMS detections to GADM districts and aggregate per district x day.

Input : yearly parquet files from download_firms_history.py (one sensor, e.g. VIIRS NOAA-20 SP)
Output: parquet with columns
    gadm_id, date,
    n_detections   - all detections with confidence != low   (matches live `fires_prev_*`,
                     because NRT data has no `type` field to filter on)
    n_vegetation   - detections with confidence nominal/high AND type == 0
                     ("presumed vegetation fire"; drives the training label)

Dates are the FIRMS acquisition date (UTC), the same field the live job counts on.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--firms-dir", type=Path, default=Path("data/raw/firms"))
    ap.add_argument("--source", default="VIIRS_NOAA20_SP")
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("data/processed/fire_counts_daily.parquet"))
    args = ap.parse_args()

    files = sorted(args.firms_dir.glob(f"{args.source}_*.parquet"))
    if not files:
        raise SystemExit(f"No {args.source}_*.parquet files in {args.firms_dir}")

    districts = gpd.read_file(args.gadm)[["GID_2", "geometry"]].rename(columns={"GID_2": "gadm_id"})
    out_frames = []
    for f in files:
        df = pd.read_parquet(f)
        df["confidence"] = df["confidence"].astype(str).str.lower().str[0]
        df = df[df["confidence"] != "l"]
        pts = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326"
        )
        joined = gpd.sjoin(pts, districts.to_crs("EPSG:4326"), how="inner", predicate="within")
        joined["is_veg"] = (joined["type"] == 0) if "type" in joined else True
        agg = (
            joined.groupby(["gadm_id", "acq_date"])
            .agg(n_detections=("is_veg", "size"), n_vegetation=("is_veg", "sum"))
            .reset_index()
            .rename(columns={"acq_date": "date"})
        )
        print(f"{f.name}: {len(df):,} detections -> {len(joined):,} inside districts", flush=True)
        out_frames.append(agg)

    out = pd.concat(out_frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out, index=False)
    print(f"wrote {len(out):,} district-day rows -> {args.out}")


if __name__ == "__main__":
    main()
