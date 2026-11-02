# ML pipeline

Everything here builds data from real sources and fails loudly when an input is missing.
No script generates synthetic data. No metric is written by hand: metrics come only from
`ml/train/train_wildfire_v2.py` output (`wildfire_v2_evaluation.json`).

## Wildfire model v2 — district x day

Run from the repo root (Python env with `backend[pipeline]` + xgboost + scikit-learn):

```bash
# 1. FIRMS detections, VIIRS NOAA-20 standard processing, India bbox (needs FIRMS map key)
FIRMS_MAP_KEY=... python ml/pipeline/download_firms_history.py \
    --source VIIRS_NOAA20_SP --start 2019-01-01 --end 2024-12-31 --out-dir data/raw/firms

# 2. GADM 4.1 India level-2 districts
python backend/scripts/load_regions.py --download   # also saves data/raw/gadm41_IND_2.json

# 3. Daily weather per district centroid from NASA POWER (no key; ~10 min)
python ml/pipeline/download_power_history.py --gadm data/raw/gadm41_IND_2.json \
    --start 2018-09-01 --end 2024-12-31 --out-dir data/raw/power

# 4. District-day fire counts (spatial join)
python ml/pipeline/build_fire_labels.py --firms-dir data/raw/firms \
    --gadm data/raw/gadm41_IND_2.json --out data/processed/fire_counts_daily.parquet

# 5. Feature table (uses backend/app/domain/features.py + fwi.py)
python ml/pipeline/build_wildfire_dataset.py --weather data/raw/power/power_daily.parquet \
    --fires data/processed/fire_counts_daily.parquet --gadm data/raw/gadm41_IND_2.json \
    --out data/processed/wildfire_dataset.parquet --climatology data/processed/climatology.json

# 6. Train + evaluate (locally or on Kaggle via ml/kaggle_wildfire_v2/)
python ml/train/train_wildfire_v2.py --dataset data/processed/wildfire_dataset.parquet \
    --climatology data/processed/climatology.json --out-dir backend/models
```

Step 6 writes `wildfire_xgb_v2.json`, `wildfire_xgb_v2_metadata.json` (features, thresholds,
metrics, sha256, climatology, fire-feature source) and `wildfire_v2_evaluation.json` (model +
baselines on validation/test). The backend loads v2 automatically (`ACTIVE_WILDFIRE_MODEL`).

### Kaggle
`ml/kaggle_wildfire_v2/` holds the kernel metadata + notebook. It expects the Kaggle dataset
`shaikhfardin05/india-district-wildfire-v2` containing `wildfire_dataset.parquet`,
`climatology.json`, `ml/train/train_wildfire_v2.py` and `backend/app/domain/features.py`.

```bash
kaggle kernels push -p ml/kaggle_wildfire_v2
kaggle kernels status shaikhfardin05/wildfire-risk-model-v2-training
kaggle kernels output shaikhfardin05/wildfire-risk-model-v2-training -p backend/models
```

## AQI: PM2.5 sub-index forecast at CPCB stations (1-3 days)
Target: the CPCB **PM2.5 sub-index of measured CPCB station PM2.5** (OpenAQ v3 daily values), at
t+1..t+3. CAMS pollutants and NASA POWER weather are input features only. No learned AQI model is
served yet; training runs on Kaggle and the result is reviewed first.

1. `download_air_history.py`: hourly Open-Meteo CAMS per district -> `data/raw/cams/<region_id>.csv.gz`
   (same source the API serves; history starts 2022-08-01).
2. `download_openaq_cpcb.py`: CPCB/caaqm PM2.5 + PM10 daily station values -> `data/raw/openaq/`.
   OpenAQ has no CPCB data between 2022-11 and 2025-02-18 (old sensor ids end 2022-10-31, new ids
   start 2025-02-19), so station data covers 2022-08..10 and 2025-02-19 onwards.
3. `aqi_sources.py`: shared rules. CAMS: invalid hours dropped (negative, PM10 >= 3270 ceiling),
   24-h means with >= 16 valid hours. Stations: day excluded if pct_complete < 75, value <= 0,
   == 985 (analyser ceiling), > 999, or inside a >= 5-day identical run. Sub-index via
   `app.domain.aqi.calculate_sub_index`. Sensor -> district by GADM polygon.
4. `build_aqi_station_dataset.py`: stations in districts with CAMS data; OpenAQ location copies
   within 300 m are merged into one station (no double counting; overlapping sensor days are
   averaged and counted). One row per station-day; features from days <= t only (station lags and
   trailing means, station PM10, station-minus-CAMS bias, district CAMS lags, POWER weather t/t-1,
   calendar, station lat/lon); missing stays NaN. Targets t+1..t+3; `ref_cams_si_t+h` is a
   comparison column, never a feature.
5. `ml/train/train_aqi_station.py` (Kaggle, `ml/kaggle_aqi_station/`): XGBoost per horizon, two
   variants (`with_station`, `no_station` = no station-derived inputs). Grid tuned on val
   (train t+h <= 2025-06-30, val 2025-07..10); test 2025-11-01..2026-10-28 scored once with a
   monthly expanding window (refit only on rows whose target day precedes the month). Spatial
   GroupKFold by district for `no_station`. Baselines: station persistence, seasonal-naive, raw
   CAMS sub-index (day t, and the target day as a reference), CAMS-target model v1. MAE, RMSE,
   R2, CPCB category accuracy, per season and per station pollution quartile.

```bash
python ml/pipeline/build_aqi_station_dataset.py --regions regions_centroids.csv \
  --gadm gadm41_IND_2.json --cams data/raw/cams --openaq data/raw/openaq \
  --power data/raw/power_aqi/power_daily.parquet --out-dir data/processed/aqi_station
# -> aqi_station_dataset.parquet, stations.csv, build_report.json (gitignored)
```

### Kaggle
Dataset `shaikhfardin05/india-aqi-station-pm25` (private): `aqi_station_dataset.parquet`,
`stations.csv`, `build_report.json`, `aqi_pm25_v1_test_predictions.parquet` (CAMS-target v1 test
forecasts, baseline only) and a copy of `train_aqi_station.py`.

```bash
kaggle kernels push -p ml/kaggle_aqi_station
kaggle kernels status shaikhfardin05/aqi-station-pm25-training
kaggle kernels output shaikhfardin05/aqi-station-pm25-training -p <dir>
```
