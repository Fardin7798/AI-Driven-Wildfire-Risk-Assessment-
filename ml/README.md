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

## AQI (next)
No learned AQI model yet (training will run on Kaggle). The old CPCB-station model was removed.

1. `download_air_history.py`: hourly Open-Meteo CAMS per district -> `data/raw/cams/<region_id>.csv.gz`
   (same source the API serves).
2. `build_aqi_dataset.py`: CPCB daily AQI per district (24-h means of PM2.5/PM10/NO2/SO2, max 8-h
   mean of CO/O3, >= 16 valid hours per pollutant, `app.domain.aqi.calculate_cpcb_aqi`), features
   known at end of day t (AQI lags 0-6, pollutant lags 0-2, 7/14-day AQI means, NASA POWER weather
   t and t-1, calendar, lat/lon), targets AQI t+1..t+3, temporal `split`, plus persistence and
   seasonal-naive baselines. Incomplete rows are dropped and counted, never filled.

```bash
python ml/pipeline/build_aqi_dataset.py --regions regions_centroids.csv --gadm gadm41_IND_2.json \
  --cams data/raw/cams --power data/raw/power_aqi/power_daily.parquet --out-dir data/processed/aqi
# -> data/processed/aqi/aqi_dataset.parquet, data/processed/aqi/baselines.json (gitignored)
```

### CAMS vs CPCB stations (validation, no training)
`validate_cams_openaq.py` pairs each CPCB/caaqm PM2.5/PM10 sensor (OpenAQ v3 daily values,
`download_openaq_cpcb.py`, days with `pct_complete >= 75`) with the CAMS 24-h mean (>= 16 valid
hours) of the district whose GADM polygon contains it, same IST date. Reports n pairs, bias
(CAMS - station), MAE and Pearson r per pollutant, overall and by season, plus a sensitivity
that also drops station artefacts (value <= 0, >= 985 ceiling, pct_complete > 100, >= 5-day
stuck runs). Nothing is filled.

```bash
python ml/pipeline/validate_cams_openaq.py --regions regions_centroids.csv --gadm gadm41_IND_2.json \
  --cams data/raw/cams --openaq data/raw/openaq --out data/processed/aqi/cams_validation.json
```
