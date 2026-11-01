# Model Card — Indian Wildfire Risk & Air Quality Platform

Status (2026-11-01): `wildfire_xgb_v2` is served for wildfire risk; districts missing any model
input fall back to Canadian FWI. All metrics below come from the Kaggle training run
(`shaikhfardin05/wildfire-risk-model-v2-training`, best iteration 133).

## 1. What is served right now

| Task | Version served | Type | Validated metrics |
|---|---|---|---|
| Wildfire risk | `wildfire_xgb_v2` | XGBoost, district x day (FWI fallback per district) | test 2024, section 2 |
| AQI 1-3 day forecast | `aqi_persistence_v1` | Persistence baseline: latest observed AQI (last 24 h) repeated for days +1..+3; no forecast without an observation | none |

`GET /api/v1/models/current` reports exactly this, read from the deployed artifacts.

## 2. Wildfire model v2

- **Question answered**: probability that a district has at least one vegetation fire on day D.
- **Unit**: district (GADM 4.1 India level 2, 676 districts) x day.
- **Label**: >= 1 NASA FIRMS VIIRS NOAA-20 detection with confidence nominal/high and
  `type == 0` (presumed vegetation fire) inside the district on day D (UTC acquisition date).
  This includes agricultural residue burning; it cannot be separated without land-cover data.
- **Features** (`WILDFIRE_V2_FEATURES` in `backend/app/domain/features.py`, 27): daily weather
  (temp max/mean, RH mean, wind max, precipitation), rolling rain/temperature/dry-day features
  over a 31-day window, FWI codes (FFMC, DMC, DC, ISI, BUI, FWI), seasonality, centroid lat/lon,
  fire counts in the previous 7/30 days (VIIRS NOAA-20, confidence != low), and the district's
  monthly fire-day rate from the training years.
- **Excluded on purpose**: `rh_min`, `et0`, `soil_moisture` (absent from the training archive),
  land-cover fractions (`wf.regions.landcover` empty in production).
- **Same code in training and live**: the dataset builder calls `extract_features`,
  `calculate_daily_fwi` and `fwi_inputs` from the backend.
- **Data**: FIRMS VIIRS NOAA-20 SP 2019-2024 (Area API), NASA POWER daily weather per district
  centroid (wind converted m/s -> km/h), FWI spun up from 2018-09-01.
- **Split**: train 2019-2022, validation 2023 (early stopping + thresholds), test 2024.
- **Baselines** (computed in the training script on the same test rows): FWI-only,
  district-month climatology, persistence (`fires_prev_7d`).
- **Risk thresholds**: chosen on validation only — moderate = recall >= 0.90, high = max F1,
  extreme = precision >= 0.80.
- **Explanations**: top 3 risk-increasing factors from XGBoost TreeSHAP (`pred_contribs`).

### Results (test year 2024, 247,416 district-days, 23.3% positive)
| Model | ROC-AUC | PR-AUC |
|---|---|---|
| **XGBoost v2** | **0.9117** | **0.7799** |
| Climatology (district-month) | 0.8790 | 0.6939 |
| Persistence (`fires_prev_7d`) | 0.8728 | 0.6856 |
| FWI only | 0.7802 | 0.4420 |

At the "high" threshold: F1 0.7022, precision 0.6701, recall 0.7376. Brier score 0.0962.
Thresholds (probability): moderate 0.1356, high 0.3421, extreme 0.5419.

### Known training/serving differences
- Training weather is NASA POWER; live weather is Open-Meteo. Same variables and units, different
  products, so small systematic biases are expected.
- Live fire history uses VIIRS NOAA-20 **NRT**; labels use **SP** (reprocessed) data.
- `fires_prev_30d` needs 30 days of detections in `wf.fire_detections`; run
  `POST /api/v1/internal/jobs/backfill_fires` once after a fresh deploy.

## 3. Retired models
- `wildfire_xgb_v1` (removed 2026-11-01): trained only on existing fire detections, target
  derived from detection confidence/FRP, features (brightness, scan, track, bright_t31) are
  measurements of a fire already burning. Leaky and impossible to compute for a district without
  a fire; in production it received zeros and returned 0.0024 for every district.
- `aqi_xgb_v1` (removed 2026-11-01): trained on CPCB station `city_day.csv` (2015-2020) while live
  data is CAMS modelled concentrations at district centroids. Will be replaced by a model trained on
  CAMS history.

## 4. Limitations
- Cloud cover and monsoon reduce satellite detections (labels are "detected fire", not "fire").
- Crop-residue burning dominates detections in parts of north India.
- District centroids represent large, heterogeneous districts with one weather point.

## 5. Disclaimer
Academic decision-support tool, not an official warning system. Consult IMD, CPCB, NDMA and
state forest departments.
