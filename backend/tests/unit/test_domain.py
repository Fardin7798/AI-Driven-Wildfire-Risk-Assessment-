from datetime import date, timedelta

from app.domain.aqi import (
    calculate_cpcb_aqi,
    calculate_sub_index,
    get_aqi_category,
)
from app.domain.features import (
    FEATURE_NAMES,
    DailyWeatherRecord,
    derive_wildfire_label,
    extract_features,
)
from app.domain.fwi import (
    calculate_daily_fwi,
)
from app.domain.risk_classes import (
    classify_fwi,
    classify_probability,
)


def test_fwi_calculation_bounds_and_propagation():
    """Verify Van Wagner FWI calculation with standard atmospheric inputs."""
    res = calculate_daily_fwi(
        temp=30.0,
        rh=25.0,
        wind=18.0,
        rain=0.0,
        month=4,
        prev_ffmc=85.0,
        prev_dmc=15.0,
        prev_dc=50.0,
    )
    assert 0.0 <= res.ffmc <= 101.0
    assert res.ffmc > 85.0  # Hot, dry, and windy conditions should increase FFMC
    assert res.dmc > 15.0
    assert res.dc > 50.0
    assert res.isi > 0.0
    assert res.bui > 0.0
    assert res.fwi > 0.0


def test_fwi_rain_damping():
    """Verify heavy precipitation reduces FFMC and drought codes."""
    dry_res = calculate_daily_fwi(temp=25.0, rh=50.0, wind=10.0, rain=0.0, month=5, prev_ffmc=90.0)
    wet_res = calculate_daily_fwi(temp=25.0, rh=50.0, wind=10.0, rain=25.0, month=5, prev_ffmc=90.0)
    assert wet_res.ffmc < dry_res.ffmc
    assert wet_res.isi < dry_res.isi
    assert wet_res.fwi < dry_res.fwi


def test_cpcb_naqi_breakpoints():
    """Verify official CPCB piecewise linear breakpoints and category thresholds."""
    # Good band (0-50)
    assert calculate_sub_index("pm25", 15.0) == 25
    assert calculate_sub_index("pm10", 25.0) == 25
    assert get_aqi_category(25) == "Good"

    # Satisfactory band (51-100)
    assert calculate_sub_index("pm25", 60.0) == 100
    assert get_aqi_category(100) == "Satisfactory"

    # Moderate band (101-200)
    assert calculate_sub_index("pm25", 90.0) == 200
    assert get_aqi_category(150) == "Moderate"

    # Severe band (401-500)
    assert calculate_sub_index("pm25", 380.0) == 452
    assert get_aqi_category(450) == "Severe"

    # Composite AQI calculation
    res = calculate_cpcb_aqi(
        {
            "pm25": 120.0,  # AQI 300 (Poor)
            "pm10": 80.0,  # AQI 80 (Satisfactory)
            "no2": 25.0,  # AQI 31 (Good)
        }
    )
    assert res.aqi == 300
    assert res.category == "Poor"
    assert res.prominent_pollutant == "PM25"


def test_risk_probability_classification():
    """Verify calibrated probability threshold mapping."""
    assert classify_probability(0.10) == "Low"
    assert classify_probability(0.35) == "Moderate"
    assert classify_probability(0.60) == "High"
    assert classify_probability(0.85) == "Extreme"

    assert classify_fwi(2.0) == "Low"
    assert classify_fwi(10.0) == "Moderate"
    assert classify_fwi(22.0) == "High"
    assert classify_fwi(35.0) == "Extreme"


def test_zero_lookahead_leakage_assertion():
    """CRITICAL TEST: Ensure future dates are strictly excluded from rolling features."""
    target_date = date(2025, 4, 15)

    # 30 days of past weather + 5 days of FUTURE weather
    history = []
    for d in range(30, 0, -1):
        history.append(
            DailyWeatherRecord(
                record_date=target_date - timedelta(days=d),
                temp_max=32.0,
                temp_mean=26.0,
                rh_min=20.0,
                rh_mean=45.0,
                wind_max=15.0,
                precip_sum=0.0,
                et0=5.0,
                soil_moisture=0.15,
            )
        )

    # Add Target Day record
    current_record = DailyWeatherRecord(
        record_date=target_date,
        temp_max=35.0,
        temp_mean=28.0,
        rh_min=18.0,
        rh_mean=40.0,
        wind_max=20.0,
        precip_sum=0.0,
        et0=6.0,
        soil_moisture=0.12,
    )
    history.append(current_record)

    # Add FUTURE records (with massive rain that would alter rolling sums if leaked)
    future_history = list(history)
    for d in range(1, 6):
        future_history.append(
            DailyWeatherRecord(
                record_date=target_date + timedelta(days=d),
                temp_max=20.0,
                temp_mean=18.0,
                rh_min=80.0,
                rh_mean=90.0,
                wind_max=50.0,
                precip_sum=200.0,  # Huge rain in future
                et0=1.0,
                soil_moisture=0.8,
            )
        )

    # Features calculated with clean history vs tainted future history
    feat_clean = extract_features(
        target_date=target_date,
        current_weather=current_record,
        weather_history=history,
        fwi_values={"ffmc": 88.0, "dmc": 20.0, "dc": 60.0, "isi": 8.0, "bui": 25.0, "fwi": 12.0},
        lat=28.6139,
        lon=77.2090,
        landcover={"tree": 0.25, "shrub": 0.15, "grass": 0.20, "crop": 0.30, "built": 0.10},
    )

    feat_tainted = extract_features(
        target_date=target_date,
        current_weather=current_record,
        weather_history=future_history,
        fwi_values={"ffmc": 88.0, "dmc": 20.0, "dc": 60.0, "isi": 8.0, "bui": 25.0, "fwi": 12.0},
        lat=28.6139,
        lon=77.2090,
        landcover={"tree": 0.25, "shrub": 0.15, "grass": 0.20, "crop": 0.30, "built": 0.10},
    )

    # Assert exact equality: future records must have ZERO effect on feature vector
    assert feat_clean == feat_tainted
    assert feat_clean["precip_sum_3d"] == 0.0
    assert feat_clean["consecutive_dry_days"] == 31.0
    assert set(feat_clean.keys()) == set(FEATURE_NAMES)


def test_derive_wildfire_label():
    """Verify wildfire label filter according to landcover class and confidence."""
    # Nominal forest fire -> 1
    assert derive_wildfire_label([{"confidence": "nominal", "landcover_class": "tree"}]) == 1
    # Low confidence -> 0
    assert derive_wildfire_label([{"confidence": "low", "landcover_class": "tree"}]) == 0
    # Cropland residue fire -> 0 when filtering for forest/vegetation {tree, shrub, grass}
    assert derive_wildfire_label([{"confidence": "high", "landcover_class": "cropland"}]) == 0
    # Empty -> 0
    assert derive_wildfire_label([]) == 0
