# Model Card — Indian Wildfire Risk & Air Quality Platform

## 1. Model Details
- **Model Name**: Wildfire Risk Predictor (XGBoost Classifier) & CAMS AQI Forecaster (Prophet)
- **Model Versions**: `wildfire_xgb_v1`, `aqi_prophet_v1`
- **Model Type**:
  - Wildfire: Gradient Boosted Decision Trees (`xgboost`) with probability calibration.
  - AQI: Additive Generalized Additive Model (`prophet`) with meteorological regressors.
- **Frameworks**: Python 3.12, XGBoost 2.x, Scikit-Learn 1.5.x, Prophet 1.1.x
- **License**: MIT License (Academic & Research Use)

## 2. Intended Use
- **Primary Use**: Daily district-level operational decision support for environmental preparedness in India.
- **Out of Scope**: Real-time tactical emergency fire suppression dispatch; not an official warning or evacuation authorization system.

## 3. Data & Splits
- **Spatial Granularity**: India District level (GADM 4.1 Level-2 boundaries, ~700 districts).
- **Time Window**: 2019 – 2025 daily time-series.
- **Temporal Split Scheme**:
  - Training Set: 2019-01-01 to 2023-12-31
  - Validation Set: 2024-01-01 to 2024-12-31 (used for early stopping & probability calibration)
  - Holdout Test Set: 2025-01-01 to 2025-12-31 (unseen final evaluation)
  - Strict zero-leakage temporal split (no random K-fold shuffling).

## 4. Evaluation Metrics & Baselines
*(Placeholders below populate upon Kaggle notebook execution)*

### Wildfire Classification Test Performance (2025 Holdout)
| Model | ROC-AUC | PR-AUC | F1-Score | Precision | Recall | Brier Score |
|---|---|---|---|---|---|---|
| Canadian FWI Baseline | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| Logistic Regression | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| Random Forest | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| **XGBoost (Calibrated)** | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |

### Air Quality Forecasting Test Performance
| Horizon | Persistence MAE | Seasonal Naive MAE | Prophet MAE | Prophet RMSE |
|---|---|---|---|---|
| Day +1 | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| Day +2 | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |
| Day +3 | *[Pending]* | *[Pending]* | *[Pending]* | *[Pending]* |

## 5. Limitations & Caveats
- Agricultural stubble burning (cropland residue) can produce rapid thermal anomalies that differ in behavior from forest canopy wildfires; ESA WorldCover 10m land cover filtering separates agricultural fires from forest fires.
- Cloud cover and heavy monsoon precipitation can obscure optical/thermal satellite sensors.

## 6. Official Disclaimer
This platform is an academic engineering decision-support tool. It does NOT constitute an official warning system. Users and agencies must consult official directives from the India Meteorological Department (IMD), Central Pollution Control Board (CPCB), National Disaster Management Authority (NDMA), and state forest departments.
