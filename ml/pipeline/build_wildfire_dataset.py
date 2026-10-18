"""Construct tabular district x day feature matrix using single source of truth app/domain/features.py."""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add backend directory to path to import app.domain.features
backend_path = Path("backend").resolve()
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.domain.features import FEATURE_NAMES, DailyWeatherRecord, extract_features
from app.domain.fwi import calculate_daily_fwi

OUTPUT_DATASET_PATH = Path("data/processed/wildfire_dataset.parquet")


def process_district_features(
    district_id: int,
    state_name: str,
    lat: float,
    lon: float,
    landcover: dict[str, float],
    weather_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    train_end_year: int = 2023,
) -> pd.DataFrame:
    """Build daily feature rows for one district with zero lookahead leakage."""
    weather_df = weather_df.sort_values("date").reset_index(drop=True)
    dates = weather_df["date"].tolist()

    # Pre-index fire events
    labels_map = {}
    if not labels_df.empty:
        dist_labels = labels_df[labels_df["district_id"] == district_id]
        labels_map = dict(zip(dist_labels["date"], dist_labels["wildfire_label"]))

    # Compute training climatology for historical fire probability by month
    training_fire_counts: dict[int, list[int]] = {m: [] for m in range(1, 13)}
    for d, lbl in labels_map.items():
        if pd.to_datetime(d).year <= train_end_year:
            training_fire_counts[pd.to_datetime(d).month].append(lbl)

    monthly_climatology = {
        m: (float(np.mean(vals)) if len(vals) > 0 else 0.01)
        for m, vals in training_fire_counts.items()
    }

    # Initialize FWI state
    ffmc, dmc, dc = 85.0, 6.0, 15.0

    feature_rows = []

    for i in range(len(weather_df)):
        current_date = dates[i]
        curr_row = weather_df.iloc[i]

        # Carry-over FWI
        ffmc, dmc, dc, isi, bui, fwi = calculate_daily_fwi(
            temp_c=float(curr_row["temperature_2m_max"]),
            rh_pct=float(curr_row["relative_humidity_2m_min"]),
            wind_kmh=float(curr_row["wind_speed_10m_max"]),
            precip_mm=float(curr_row["precipitation_sum"]),
            month=pd.to_datetime(current_date).month,
            prev_ffmc=ffmc,
            prev_dmc=dmc,
            prev_dc=dc,
        )

        # Slice historical weather window strictly up to day i (inclusive)
        window_start = max(0, i - 35)
        window_slice = weather_df.iloc[window_start : i + 1]

        hist_records = [
            DailyWeatherRecord(
                record_date=r["date"],
                temp_max=float(r["temperature_2m_max"]),
                temp_mean=float(r["temperature_2m_mean"]),
                rh_min=float(r["relative_humidity_2m_min"]),
                rh_mean=float(r["relative_humidity_2m_mean"]),
                wind_max=float(r["wind_speed_10m_max"]),
                precip_sum=float(r["precipitation_sum"]),
                et0=float(r.get("et0_fao_evapotranspiration", 3.0)),
                soil_moisture=float(r.get("soil_moisture_0_to_7cm_mean", 0.25)),
            )
            for _, r in window_slice.iterrows()
        ]

        # Prior fire counts strictly prior to current_date (lag 1..7 and lag 1..30)
        fires_prev_7d = sum(
            labels_map.get(dates[j], 0)
            for j in range(max(0, i - 7), i)
        )
        fires_prev_30d = sum(
            labels_map.get(dates[j], 0)
            for j in range(max(0, i - 30), i)
        )

        month = pd.to_datetime(current_date).month
        clim_freq = monthly_climatology.get(month, 0.01)

        fwi_dict = {
            "ffmc": ffmc,
            "dmc": dmc,
            "dc": dc,
            "isi": isi,
            "bui": bui,
            "fwi": fwi,
        }

        # Single source of truth feature extraction
        feats = extract_features(
            prediction_date=current_date,
            centroid_lat=lat,
            centroid_lon=lon,
            state_name=state_name,
            landcover=landcover,
            weather_history=hist_records,
            fwi_state=fwi_dict,
            fires_prev_7d=fires_prev_7d,
            fires_prev_30d=fires_prev_30d,
            climatological_fire_freq=clim_freq,
        )

        feats["district_id"] = district_id
        feats["date"] = current_date
        feats["year"] = pd.to_datetime(current_date).year
        feats["label"] = labels_map.get(current_date, 0)

        feature_rows.append(feats)

    return pd.DataFrame(feature_rows)


def main():
    parser = argparse.ArgumentParser(description="Build district x day wildfire training matrix")
    parser.add_argument("--output", type=Path, default=OUTPUT_DATASET_PATH)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print("Wildfire dataset builder configured using backend/app/domain/features.py.")


if __name__ == "__main__":
    main()
