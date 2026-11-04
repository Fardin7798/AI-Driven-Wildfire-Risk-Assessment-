# Model Card — Indian Wildfire Risk & Air Quality Platform

Status (2026-11-04, branch `backend`, not yet deployed): `wildfire_xgb_v3` is the active
wildfire model; districts missing any model input fall back to Canadian FWI. AQI forecasts come
from `aqi_station_xgb_v3` (model B). Wildfire metrics below come from the Kaggle training run
(`shaikhfardin05/wildfire-risk-model-v3-training`, GPU, best iteration 344).

## 1. What is served right now

| Task | Version served | Type | Validated metrics |
|---|---|---|---|
| Wildfire risk | `wildfire_xgb_v3` | XGBoost, district x day (FWI fallback per district) | test 2025, section 2 |
| AQI 1-3 day forecast | `aqi_station_xgb_v3` | XGBoost model B (no-station), one booster per horizon: CPCB PM2.5 sub-index at t+1..t+3 from CAMS + Open-Meteo inputs at the district centroid | test 2025-11-01..2026-10-28, section 3 (second look at test) |

`GET /api/v1/models/current` reports exactly this, read from the deployed artifacts
(`backend/models/wildfire_xgb_v3/`: booster, metadata with sha256 + thresholds + climatology,
evaluation).

## 2. Wildfire model v3

- **Question answered**: probability that a district has at least one vegetation fire on day D.
- **Unit**: district (GADM 4.1 India level 2, 676 districts) x day.
- **Label**: >= 1 NASA FIRMS VIIRS NOAA-20 detection with confidence nominal/high and
  `type == 0` (presumed vegetation fire) inside the district on day D (UTC acquisition date).
  This includes agricultural residue burning; it cannot be separated without land-cover data.
  Labels are identical to v2's on 2019-2024 (0 mismatches over 1,481,792 district-days).
- **Features** (`WILDFIRE_V2_FEATURES` in `backend/app/domain/features.py`, 27, same list as v2):
  daily weather (temp max/mean, RH mean, wind max, precipitation), rolling rain/temperature/dry-day
  features over a 31-day window, FWI codes (FFMC, DMC, DC, ISI, BUI, FWI), seasonality, centroid
  lat/lon, fire counts in the previous 7/30 days (VIIRS NOAA-20, confidence != low), and the
  district's monthly fire-day rate from the training years (2019-2023).
- **Excluded on purpose**: `rh_min`, `et0`, `soil_moisture`, land-cover fractions
  (`wf.regions.landcover` empty in production).
- **Same code in training and live**: the dataset builder calls `extract_features`,
  `calculate_daily_fwi` and `fwi_inputs` from the backend.
- **Weather (what changed from v2)**: ECMWF IFS HRES 9 km via Open-Meteo (`models=ecmwf_ifs`),
  the same model the live API serves, instead of NASA POWER. Day = Open-Meteo's
  `timezone=Asia/Kolkata` day, i.e. 19:00..19:00 UTC (Open-Meteo truncates +05:30 to 5 h).
  temp_max / temp_min = max / min of the 24 hourly temperature_2m values of that day;
  temp_mean, rh_mean, wind_max, precip_sum = Open-Meteo daily aggregates.
- **Data**: FIRMS VIIRS NOAA-20 SP 2018-12..2025-12 (Area API), IFS weather per district
  (Open-Meteo cell selection reproduced), FWI spun up from 2018-09-01.
- **Split**: train 2019-2023, validation 2024 (early stopping + thresholds), test 2025.
  Params, seed and features are v2's fixed ones (no grid search).
- **Baselines** (computed in the training script on the same test rows): FWI-only,
  district-month climatology, persistence (`fires_prev_7d`), and deployed v2 on the same rows.
- **Risk thresholds**: chosen on validation only — moderate = recall >= 0.90, high = max F1,
  extreme = precision >= 0.80.
- **Explanations**: top 3 risk-increasing factors from XGBoost TreeSHAP (`pred_contribs`).

### Results (test year 2025, 246,740 district-days, 23.85% positive)
| Model | ROC-AUC | PR-AUC | F1 (own "high" threshold) |
|---|---|---|---|
| **XGBoost v3** | **0.9232** | **0.8172** | **0.7268** |
| XGBoost v2 (deployed, same rows, IFS weather, v2 climatology + thresholds) | 0.9199 | 0.8093 | 0.7226 |
| Climatology (district-month) | 0.8889 | 0.7264 | |
| Persistence (`fires_prev_7d`) | 0.8849 | 0.7316 | |
| FWI only | 0.8003 | 0.5060 | |

v3 at the "high" threshold: precision 0.7000, recall 0.7557, Brier 0.0902. Thresholds
(probability): moderate 0.143, high 0.3256, extreme 0.5574. Validation 2024: ROC 0.9146,
PR 0.7853, F1 0.7069. The v3 - v2 gain is small (+0.003 ROC, +0.008 PR); the main reason for v3 is
that its training weather is the same product, model and day boundary as live weather.

**Test disclosure.** The 2025 test year was exposed once before the official run: a local CPU
smoke run of `train_wildfire_v3.py` on a 60k-row train subsample (to check the script end to end)
printed 2025 test metrics for that throwaway model (ROC ~0.921) and for v2 on 2025 rows. Its
outputs were deleted and nothing (features, params, thresholds, rounds) was tuned or chosen from
it. The numbers above are the single official Kaggle run.

### Known training/serving differences
- Live weather for "today" (scored at 01:10 IST) is an IFS forecast at short lead time; training
  used Open-Meteo's archived IFS runs (Historical Forecast API). Same model, cell and derivation;
  past days agree within API rounding (0.05 C, 0.5 % RH, 0.05 km/h, 0.0 mm; 3 districts,
  2026-10-25..11-01).
- Live fire history uses VIIRS NOAA-20 **NRT**; labels use **SP** (reprocessed) data.
- IFS model upgrades (49r1 2024-11-12, 50r1 2026-05-12) could shift weather; not separable from
  weather in the audit.
- `fires_prev_30d` needs 30 days of detections in `wf.fire_detections`; run
  `POST /api/v1/internal/jobs/backfill_fires` once after a fresh deploy.

### Missing weather (no imputation)
- Training never saw a missing value (0 missing hourly values in the IFS extraction) and
  `train_wildfire_v3.py` refuses any NaN feature. XGBoost's native NaN handling is never relied on.
- Live: a day with fewer than 24 hourly temperatures, or any null hour, has temp_max/temp_min =
  NULL (counted and logged by `ingest_weather`); any value the API does not return stays NULL.
- A district-day is scored only when all 31 days of its rolling window (target day and 30 before)
  have temp_max, temp_mean, rh_mean, wind_max and precip_sum; otherwise `predict_risk` skips it and
  logs the reason (`weather_window_incomplete`, `no_fwi_state_today`, `no_centroid`). FWI state
  carries over only from the previous day; any gap restarts from the standard start-up codes, as
  in the dataset builder.
- There is no fallback weather source: another dataset would feed the model different weather.

## 3. AQI model B v3 (`aqi_station_xgb_v3`)

- **Question answered**: CPCB PM2.5 sub-index (24 h mean, IST day) of a district on day t+h,
  h = 1..3, from inputs known at origin day t (served origin = yesterday IST).
- **Variant served**: `no_station` (43 features): CAMS PM2.5 sub-index lags/rolling means,
  CAMS PM2.5/PM10/NO2/SO2/CO/O3 lags, Open-Meteo Historical Forecast daily weather (t, t-1),
  seasonality, district-centroid lat/lon. No station observation is needed at serving time.
- **Labels**: CPCB station PM2.5 (training only). Districts far from any training station are
  flagged `extrapolated` (coverage.json: extrapolated = nearest training station > 200 km OR centroid outside the convex hull of the training stations).
- **Split**: train target day <= 2025-06-30, validation 2025-07-01..2025-10-31
  (grid search), test 2025-11-01..2026-10-28 scored with monthly expanding-window refits.
- **Serving**: daily job `forecast_aqi` (10:30 IST) writes `wf.aqi_forecasts_b`; districts without
  complete inputs get a reason in `wf.aqi_forecast_skips` and no value.
- **Test disclosure**: second look at the test period: 2025-11-01..2026-10-28 was already scored by run v2 (aqi_station_xgb_v1: NASA POWER weather, station lat/lon). v3 changes the inputs (Open-Meteo Historical Forecast weather, district-centroid lat/lon) after v2's test results were seen; protocol, grid, splits and seed are unchanged. Its test numbers are not an untouched test.

### Results (test, MAE in PM2.5 sub-index points, `aqi_station_evaluation.json`)
| Model | h1 | h2 | h3 |
|---|---|---|---|
| **Model B v3 (no-station)** | 37.59 | 39.355 | 41.131 |
| Raw CAMS at t (`cams_t`) | 60.928 | 63.626 | 64.739 |
| Station persistence (needs a station observation; not available live) | 22.875 | 30.27 | 33.234 |
| Station seasonal naive (needs station observations; not available live) | 37.134 | 37.283 | 37.264 |

Model B beats raw CAMS on every horizon. The station baselines are better where a CPCB station
reports, but they cannot produce a value for a district without one, which model B is for.

## 4. Retired models
- `wildfire_xgb_v2` (replaced 2026-11-04 by v3): same features and params, trained on NASA POWER
  weather 2019-2022 (val 2023, test 2024: ROC 0.9117, PR 0.7799). Live weather was Open-Meteo, a
  different product. Artifacts backed up outside the repo and in git history (up to d064070).
- `wildfire_xgb_v1` (removed 2026-11-01): trained only on existing fire detections, target
  derived from detection confidence/FRP, features (brightness, scan, track, bright_t31) are
  measurements of a fire already burning. Leaky and impossible to compute for a district without
  a fire; in production it received zeros and returned 0.0024 for every district.
- `aqi_xgb_v1` (removed 2026-11-01): trained on CPCB station `city_day.csv` (2015-2020) while live
  data is CAMS modelled concentrations at district centroids. Replaced by `aqi_station_xgb_v3`.
- `aqi_persistence_v1` (removed 2026-11-03): latest observed AQI repeated for days +1..+3.
  Replaced by model B; its table `wf.aq_forecasts` is dropped by migration 004.

## 5. Limitations
- Cloud cover and monsoon reduce satellite detections (labels are "detected fire", not "fire").
- Crop-residue burning dominates detections in parts of north India.
- District centroids represent large, heterogeneous districts with one weather point.

## 6. Disclaimer
Academic decision-support tool, not an official warning system. Consult IMD, CPCB, NDMA and
state forest departments.
