from datetime import date

from app.ml.aqi_forecaster import forecast_aqi_trajectory
from app.ml.wildfire_predictor import predict_wildfire_risk


def test_wildfire_predictor_fwi_fallback():
    """Verify that when no model weights are present, predictor cleanly falls back to FWI engine."""
    sample_features = {
        "fwi": 25.4,
        "wind_max": 24.0,
        "temp_max": 38.0,
        "ffmc": 91.5,
        "consecutive_dry_days": 14.0,
        "bui": 30.0,
    }
    result = predict_wildfire_risk(sample_features, model_version="non_existent_model_v99")

    assert result.is_fallback is True
    assert result.model_version == "fwi_fallback"
    assert result.risk_class == "High"
    assert 0.0 <= result.probability <= 1.0
    assert result.fwi_value == 25.4

    # Verify top 3 factors present
    factors = result.top_factors.get("factors", [])
    assert len(factors) == 3
    assert all("factor" in f and "value" in f and "unit" in f for f in factors)


def test_aqi_forecaster_trajectory():
    """Verify 1 to 3 day AQI trajectory with persistence and dispersion logic."""
    target_date = date(2026, 4, 15)
    forecasts = forecast_aqi_trajectory(
        target_date=target_date,
        current_aqi=180,
        current_pm25=75.0,
        current_pm10=150.0,
        weather_forecast=[
            {"wind_max": 25.0, "precip_sum": 0.0},  # Day +1: high wind (dispersion)
            {"wind_max": 10.0, "precip_sum": 10.0},  # Day +2: rain (washout)
            {"wind_max": 8.0, "precip_sum": 0.0},  # Day +3: calm
        ],
    )

    assert len(forecasts) == 3
    assert forecasts[0]["horizon_days"] == 1
    assert forecasts[1]["horizon_days"] == 2
    assert forecasts[2]["horizon_days"] == 3
    assert all("pm25_pred" in f and "aqi_pred" in f and "aqi_category" in f for f in forecasts)


def test_wildfire_predictor_real_model_loading(tmp_path):
    """Verify loading active model artifact built inside tmp_path at test time."""
    import hashlib
    import json

    import numpy as np
    import xgboost as xgb

    from app.domain.features import FEATURE_NAMES
    from app.ml.loader import ModelLoader

    version = "test_xgb_v1"
    model_file = tmp_path / f"{version}.json"
    meta_file = tmp_path / f"{version}_metadata.json"

    X = np.random.uniform(0.1, 1.0, size=(20, len(FEATURE_NAMES)))
    y = np.random.choice([0, 1], size=20)
    clf = xgb.XGBClassifier(n_estimators=3, max_depth=2, random_state=42)
    clf.fit(X, y)
    clf.save_model(str(model_file))

    with open(model_file, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    meta = {
        "model_type": "wildfire",
        "version": version,
        "feature_list": FEATURE_NAMES,
        "metrics": {"roc_auc": 0.85},
        "thresholds": {"moderate": 0.35, "high": 0.60, "extreme": 0.80},
        "artifact_path": str(model_file),
        "sha256": sha256,
        "is_active": True,
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    loader = ModelLoader(model_dir=str(tmp_path))
    sample_features = dict.fromkeys(FEATURE_NAMES, 0.5)
    sample_features["fwi"] = 25.4

    result = predict_wildfire_risk(sample_features, model_version=version, loader=loader)
    assert result.is_fallback is False
    assert result.model_version == version
    assert 0.0 <= result.probability <= 1.0
    assert result.risk_class in ["Low", "Moderate", "High", "Extreme"]
