# ML Training & Feature Pipeline

This directory contains the dataset preparation pipelines, exploratory data analysis, and model training workflows for the **AI-Driven Wildfire Risk Assessment & Air Quality Platform**.

## Architecture & Split Protocol

- **Time-Based Evaluation Split**:
  - **Train Fold**: 2019 – 2023 (Historical base)
  - **Validation Fold**: 2024 (Hyperparameter tuning, probability calibration, risk threshold determination)
  - **Holdout Test Fold**: 2025 (Final unbiased performance evaluation)
  - *No random train/test splitting is used to prevent spatial-temporal leakage.*
- **Zero Lookahead Leakage Guarantee**:
  - Feature extraction uses `backend/app/domain/features.py` as the single source of truth.
  - All weather rolling metrics and fire history lags only utilize data strictly preceding the prediction date.

## Directory Structure

```
ml/
├── pipeline/
│   ├── download_firms_history.py     # NASA FIRMS Country Yearly Summary scraper / ingest
│   ├── download_weather_history.py   # Resumable Open-Meteo ERA5 / NASA POWER downloader
│   ├── download_air_history.py       # CAMS criteria pollutants historical downloader
│   ├── build_fire_labels.py          # Spatial join to districts + landcover filtering
│   ├── build_wildfire_dataset.py     # District x Day dataset matrix construction
│   ├── build_aqi_dataset.py          # AQI lag & meteorological forecasting matrix
│   └── validate_dataset.py           # Pre-flight data quality & leak validation checks
├── notebooks/
│   ├── 01_eda.ipynb                  # Exploratory Data Analysis
│   ├── 02_train_wildfire_kaggle.ipynb # XGBoost vs RF vs FWI Baseline training & SHAP
│   └── 03_train_aqi_kaggle.ipynb     # Prophet vs Persistence forecasting benchmarks
├── reports/
│   └── dataset_report.md             # Dataset quality, balance, and feature summaries
└── artifacts/                        # Gitignored export directory for trained models
```

## Running the Pipeline

1. **Download Raw Data**:
   ```bash
   python ml/pipeline/download_firms_history.py
   python ml/pipeline/download_weather_history.py --start-year 2019 --end-year 2025
   python ml/pipeline/download_air_history.py --start-year 2022 --end-year 2025
   ```

2. **Generate Labels & Matrices**:
   ```bash
   python ml/pipeline/build_fire_labels.py
   python ml/pipeline/build_wildfire_dataset.py
   python ml/pipeline/build_aqi_dataset.py
   ```

3. **Validate Dataset**:
   ```bash
   python ml/pipeline/validate_dataset.py
   ```

4. **Train Models**:
   - Run `ml/notebooks/02_train_wildfire_kaggle.ipynb` locally or upload `data/processed/` to Kaggle.
   - Exported artifacts (`wildfire_xgb_v1.json` + `wildfire_v1_metadata.json`) are copied into `backend/models/`.
