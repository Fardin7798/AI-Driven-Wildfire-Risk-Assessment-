"""Construct AQI trajectory forecasting dataset with synoptic weather regressors and baselines."""

import argparse
from pathlib import Path
import pandas as pd

OUTPUT_AQI_DATASET_PATH = Path("data/processed/aqi_dataset.parquet")


def build_aqi_features_and_targets(
    aq_df: pd.DataFrame, weather_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge air quality with meteorological regressors and construct multi-horizon targets."""
    # Ensure datetime formatting
    aq_df["date"] = pd.to_datetime(aq_df["date"]).dt.date
    weather_df["date"] = pd.to_datetime(weather_df["date"]).dt.date

    merged = pd.merge(aq_df, weather_df, on=["district_id", "date"], how="inner")
    merged = merged.sort_values(["district_id", "date"]).reset_index(drop=True)

    rows = []
    # Process per district time-series
    for dist_id, group in merged.groupby("district_id"):
        group = group.copy().reset_index(drop=True)
        pm25 = group["pm2_5_mean"].values if "pm2_5_mean" in group else group["pm25"].values

        for i in range(len(group)):
            # Need at least 7 days of history for seasonal naive baseline
            if i < 7:
                continue

            current_row = group.iloc[i].to_dict()

            # Lags (t-1, t-2, t-7)
            current_row["pm25_t0"] = float(pm25[i])
            current_row["pm25_lag_1"] = float(pm25[i - 1])
            current_row["pm25_lag_2"] = float(pm25[i - 2])
            current_row["pm25_lag_7"] = float(pm25[i - 7])

            # Forward forecasting targets (t+1, t+2, t+3)
            current_row["pm25_target_h1"] = float(pm25[i + 1]) if (i + 1) < len(pm25) else None
            current_row["pm25_target_h2"] = float(pm25[i + 2]) if (i + 2) < len(pm25) else None
            current_row["pm25_target_h3"] = float(pm25[i + 3]) if (i + 3) < len(pm25) else None

            # Baselines
            current_row["baseline_persistence_h1"] = float(pm25[i])
            current_row["baseline_seasonal_7d"] = float(pm25[i - 7])

            rows.append(current_row)

    df_out = pd.DataFrame(rows)
    return df_out


def main():
    parser = argparse.ArgumentParser(description="Build AQI multi-horizon forecasting matrix")
    parser.add_argument("--output", type=Path, default=OUTPUT_AQI_DATASET_PATH)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print("AQI dataset builder ready.")


if __name__ == "__main__":
    main()
