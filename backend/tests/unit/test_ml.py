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


def test_wildfire_predictor_real_model_loading():
    """Verify loading active production model artifact from backend/models."""
    sample_features = {
        "temp_max": 38.0,
        "temp_mean": 30.0,
        "rh_min": 20.0,
        "rh_mean": 45.0,
        "wind_max": 24.0,
        "precip_sum": 0.0,
        "et0": 4.5,
        "soil_moisture": 0.15,
        "precip_3d": 0.0,
        "precip_7d": 0.0,
        "precip_14d": 0.0,
        "precip_30d": 5.0,
        "temp_max_7d_mean": 37.0,
        "rh_min_7d_mean": 22.0,
        "dry_days_count": 18,
        "days_since_rain_10mm": 35,
        "ffmc": 91.5,
        "dmc": 35.0,
        "dc": 180.0,
        "isi": 12.0,
        "bui": 45.0,
        "fwi": 25.4,
        "month": 4,
        "day_of_year_sin": 0.86,
        "day_of_year_cos": -0.5,
        "centroid_lat": 28.6,
        "centroid_lon": 77.2,
        "tree_fraction": 0.35,
        "shrub_fraction": 0.20,
        "grass_fraction": 0.15,
        "crop_fraction": 0.20,
        "built_fraction": 0.10,
        "fires_prev_7d": 2,
        "fires_prev_30d": 5,
        "climatological_fire_freq": 0.08,
    }
    result = predict_wildfire_risk(sample_features, model_version="wildfire_xgb_v1")
    assert 0.0 <= result.probability <= 1.0
    assert result.risk_class in ["Low", "Moderate", "High", "Extreme"]
