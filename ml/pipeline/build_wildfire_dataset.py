"""Build the district x day wildfire training table with the backend's own feature code.

Every feature row is produced by `app.domain.features.extract_features` and FWI by
`app.domain.fwi.calculate_daily_fwi` + `fwi_inputs`, i.e. exactly the functions the live
`predict_risk` job calls. Rolling features see only the last ROLLING_WINDOW_DAYS days up to
day D; fire-history features see only days strictly before D.

Label (day D): 1 if the district had >= 1 VIIRS NOAA-20 detection with confidence nominal/high
and type == 0 (presumed vegetation fire) on day D, else 0. This includes agricultural
residue burning; FIRMS cannot separate it from forest fire without land-cover data.

Inputs:
  --weather  power_daily.parquet        (download_power_history.py)
  --fires    fire_counts_daily.parquet  (build_fire_labels.py)
  --gadm     GADM 4.1 level-2 GeoJSON
Outputs:
  --out          wildfire_dataset.parquet  (gadm_id, date, split, label, WILDFIRE_V2_FEATURES)
  --climatology  climatology.json          {gadm_id: [12 monthly fire-day rates]} from TRAIN years only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from app.domain.features import (  # noqa: E402
    ROLLING_WINDOW_DAYS,
    WILDFIRE_V2_FEATURES,
    DailyWeatherRecord,
    extract_features,
)
from app.domain.fwi import FWI_STARTUP, calculate_daily_fwi, fwi_inputs  # noqa: E402


def split_of(d: date, train_end: int, val_year: int) -> str:
    if d.year <= train_end:
        return "train"
    if d.year == val_year:
        return "val"
    return "test"


def compute_climatology(fires: pd.DataFrame, gadm_ids: list[str], train_years: list[int]) -> dict:
    """Monthly share of days with a vegetation fire, per district, from training years only."""
    f = fires[fires["n_vegetation"] > 0].copy()
    f["date"] = pd.to_datetime(f["date"])
    f = f[f["date"].dt.year.isin(train_years)]
    fire_days = f.groupby([f["gadm_id"], f["date"].dt.month]).size()
    days_in_month = (
        pd.Series(pd.date_range(f"{train_years[0]}-01-01", f"{train_years[-1]}-12-31"))
        .dt.month.value_counts()
        .sort_index()
    )
    clim = {}
    for gid in gadm_ids:
        clim[gid] = [
            round(float(fire_days.get((gid, m), 0)) / float(days_in_month[m]), 6)
            for m in range(1, 13)
        ]
    return clim


def build_district(
    gid: str,
    lat: float,
    lon: float,
    w: pd.DataFrame,
    det: dict[date, int],
    veg: dict[date, int],
    clim: list[float],
    start: date,
) -> list[dict]:
    rows: list[dict] = []
    recs: list[DailyWeatherRecord] = []
    state = dict(FWI_STARTUP)
    for r in w.itertuples(index=False):
        d: date = r.date
        rec = DailyWeatherRecord(
            record_date=d,
            temp_max=r.temp_max,
            temp_mean=r.temp_mean,
            rh_min=None,
            rh_mean=r.rh_mean,
            wind_max=r.wind_max,
            precip_sum=r.precip_sum,
            et0=None,
            soil_moisture=None,
        )
        recs.append(rec)
        inputs = fwi_inputs(r.temp_max, r.rh_mean, r.wind_max, r.precip_sum)
        if inputs is None:  # gap: restart FWI from standard start-up codes
            state = dict(FWI_STARTUP)
            continue
        res = calculate_daily_fwi(
            month=d.month,
            prev_ffmc=state["ffmc"],
            prev_dmc=state["dmc"],
            prev_dc=state["dc"],
            **inputs,
        )
        state = {"ffmc": res.ffmc, "dmc": res.dmc, "dc": res.dc}
        if d < start:
            continue  # spin-up period for FWI codes and rolling windows

        f7 = sum(det.get(d - timedelta(days=k), 0) for k in range(1, 8))
        f30 = f7 + sum(det.get(d - timedelta(days=k), 0) for k in range(8, 31))
        feats = extract_features(
            target_date=d,
            current_weather=rec,
            weather_history=recs[-ROLLING_WINDOW_DAYS:],
            fwi_values={
                "ffmc": res.ffmc,
                "dmc": res.dmc,
                "dc": res.dc,
                "isi": res.isi,
                "bui": res.bui,
                "fwi": res.fwi,
            },
            lat=lat,
            lon=lon,
            landcover={},
            fires_prev_7d=f7,
            fires_prev_30d=f30,
            climatological_fire_freq=clim[d.month - 1],
        )
        row = {k: feats[k] for k in WILDFIRE_V2_FEATURES}
        row.update(gadm_id=gid, date=d, label=int(veg.get(d, 0) > 0))
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--weather", type=Path, required=True)
    ap.add_argument("--fires", type=Path, required=True)
    ap.add_argument("--gadm", type=Path, required=True)
    ap.add_argument("--start", type=date.fromisoformat, default=date(2019, 1, 1))
    ap.add_argument("--train-end-year", type=int, default=2022)
    ap.add_argument("--val-year", type=int, default=2023)
    ap.add_argument("--out", type=Path, default=Path("data/processed/wildfire_dataset.parquet"))
    ap.add_argument("--climatology", type=Path, default=Path("data/processed/climatology.json"))
    args = ap.parse_args()

    gdf = gpd.read_file(args.gadm)
    cent = gdf.geometry.centroid
    meta = {
        row.GID_2: (float(c.y), float(c.x)) for row, c in zip(gdf.itertuples(), cent, strict=True)
    }

    weather = pd.read_parquet(args.weather)
    weather["date"] = pd.to_datetime(weather["date"]).dt.date
    fires = pd.read_parquet(args.fires)
    fires["date"] = pd.to_datetime(fires["date"]).dt.date
    if weather.empty or fires.empty:
        raise SystemExit("Weather or fire input is empty; refusing to build a dataset")

    train_years = list(range(args.start.year, args.train_end_year + 1))
    clim = compute_climatology(fires, list(meta), train_years)
    args.climatology.parent.mkdir(parents=True, exist_ok=True)
    args.climatology.write_text(json.dumps({"train_years": train_years, "monthly_rate": clim}))

    det_by = {
        g: dict(zip(x["date"], x["n_detections"], strict=True)) for g, x in fires.groupby("gadm_id")
    }
    veg_by = {
        g: dict(zip(x["date"], x["n_vegetation"], strict=True)) for g, x in fires.groupby("gadm_id")
    }

    all_rows: list[dict] = []
    for i, (gid, w) in enumerate(weather.sort_values(["gadm_id", "date"]).groupby("gadm_id")):
        lat, lon = meta[gid]
        all_rows.extend(
            build_district(
                gid, lat, lon, w, det_by.get(gid, {}), veg_by.get(gid, {}), clim[gid], args.start
            )
        )
        if (i + 1) % 100 == 0:
            print(f"{i + 1} districts processed", flush=True)

    df = pd.DataFrame(all_rows)
    df["split"] = [split_of(d, args.train_end_year, args.val_year) for d in df["date"]]
    df[WILDFIRE_V2_FEATURES] = df[WILDFIRE_V2_FEATURES].astype(np.float32)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"wrote {len(df):,} rows, positive rate {df['label'].mean():.4f} -> {args.out}")
    print(df.groupby("split")["label"].agg(["size", "mean"]))


if __name__ == "__main__":
    main()
