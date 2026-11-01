# Model Card — Indian Wildfire Risk & Air Quality Platform

Status (2026-11-01): **no learned wildfire model is deployed yet.** The API serves the Canadian
FWI fallback until `wildfire_xgb_v2` is trained and committed. No metric below may be quoted
until it comes from a real training run's `wildfire_v2_evaluation.json`.

## 1. What is served right now

| Task | Version served | Type | Validated metrics |
|---|---|---|---|
| Wildfire risk | `fwi_fallback` | Canadian FWI (Van Wagner 1987) danger classes | none |
| AQI 1-3 day forecast | `aqi_persistence_v1` | Rule-based persistence + wind/rain dispersion | none |

`GET /api/v1/models/current` reports exactly this, read from the deployed artifacts.

## 2. Wildfire model v2 (to be trained)

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

### Known training/serving differences
- Training weather is NASA POWER; live weather is Open-Meteo. Same variables and units, different
  products, so small systematic biases are expected.
- Live fire history uses VIIRS NOAA-20 **NRT**; labels use **SP** (reprocessed) data.

## 3. Retired models
- `wildfire_xgb_v1` (removed 2026-11-01): trained only on existing fire detections, target
  derived from detection confidence/FRP, features (brightness, scan, track, bright_t31) are
  measurements of a fire already burning. Leaky and impossible to compute for a district without
  a fire; in production it received zeros and returned 0.0024 for every district.
- `aqi_xgb_v1` (kept in `backend/models/`, **not served**): trained on CPCB station `city_day.csv`
  (2015-2020) while live data is CAMS modelled concentrations at district centroids. Not wired
  until trained on the same source it will be served on.

## 4. Limitations
- Cloud cover and monsoon reduce satellite detections (labels are "detected fire", not "fire").
- Crop-residue burning dominates detections in parts of north India.
- District centroids represent large, heterogeneous districts with one weather point.

## 5. Disclaimer
Academic decision-support tool, not an official warning system. Consult IMD, CPCB, NDMA and
state forest departments.
