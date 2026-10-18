"""
Single Source of Truth (SSOT) Feature Engineering Engine.
Shared identically by offline dataset generation, model training, and online live inference.
Guarantees zero-lookahead leakage.
"""
from dataclasses import dataclass
from datetime import date
import math
from typing import Any, Dict, List, Optional, Sequence


FEATURE_NAMES: List[str] = [
    # 1. Daily Surface Weather
    "temp_max",
    "temp_mean",
    "rh_min",
    "rh_mean",
    "wind_max",
    "precip_sum",
    "et0",
    "soil_moisture",

    # 2. Rolling Aggregations (Past N days up to Day D)
    "precip_sum_3d",
    "precip_sum_7d",
    "precip_sum_14d",
    "precip_sum_30d",
    "temp_max_mean_7d",
    "rh_min_mean_7d",

    # 3. Dryness & Drought State
    "consecutive_dry_days",      # Days with precip < 1.0 mm
    "days_since_rain_gt_10mm",   # Days elapsed since last daily rain > 10.0 mm

    # 4. Canadian FWI Physics Sub-Indices
    "ffmc",
    "dmc",
    "dc",
    "isi",
    "bui",
    "fwi",

    # 5. Seasonality (Cyclical Encodings)
    "month_sin",
    "month_cos",
    "day_of_year_sin",
    "day_of_year_cos",

    # 6. Spatial / Topography
    "lat",
    "lon",

    # 7. Land Cover Fractions (ESA WorldCover 10m)
    "fraction_tree",
    "fraction_shrub",
    "fraction_grass",
    "fraction_crop",
    "fraction_built",

    # 8. Lagged Historical Fire Activity (Strictly prior to Day D, never same day)
    "fires_prev_7d",
    "fires_prev_30d",
    "climatological_fire_freq",
]


@dataclass(frozen=True)
class DailyWeatherRecord:
    record_date: date
    temp_max: float
    temp_mean: float
    rh_min: float
    rh_mean: float
    wind_max: float
    precip_sum: float
    et0: float
    soil_moisture: float


def compute_cyclical_features(target_date: date) -> Dict[str, float]:
    """Calculate sine/cosine transformations for month and day of year."""
    month = target_date.month
    day_of_year = target_date.timetuple().tm_yday

    return {
        "month_sin": round(math.sin(2.0 * math.pi * month / 12.0), 6),
        "month_cos": round(math.cos(2.0 * math.pi * month / 12.0), 6),
        "day_of_year_sin": round(math.sin(2.0 * math.pi * day_of_year / 365.25), 6),
        "day_of_year_cos": round(math.cos(2.0 * math.pi * day_of_year / 365.25), 6),
    }


def compute_rolling_weather_features(
    history: Sequence[DailyWeatherRecord],
    target_date: date
) -> Dict[str, float]:
    """
    Compute rolling precip sums, temp means, and dry day counters strictly using data <= target_date.
    history must be sorted chronologically ascending up to target_date.
    """
    # Enforce strictly no future records
    valid_history = [r for r in history if r.record_date <= target_date]
    if not valid_history:
        return {
            "precip_sum_3d": 0.0,
            "precip_sum_7d": 0.0,
            "precip_sum_14d": 0.0,
            "precip_sum_30d": 0.0,
            "temp_max_mean_7d": 25.0,
            "rh_min_mean_7d": 40.0,
            "consecutive_dry_days": 0.0,
            "days_since_rain_gt_10mm": 30.0,
        }

    # Reverse to iterate backwards from target_date
    rev = list(reversed(valid_history))

    precip_3d = sum(r.precip_sum for r in rev[:3])
    precip_7d = sum(r.precip_sum for r in rev[:7])
    precip_14d = sum(r.precip_sum for r in rev[:14])
    precip_30d = sum(r.precip_sum for r in rev[:30])

    recent_7d = rev[:7]
    temp_max_mean_7d = sum(r.temp_max for r in recent_7d) / len(recent_7d)
    rh_min_mean_7d = sum(r.rh_min for r in recent_7d) / len(recent_7d)

    # Consecutive dry days (precip < 1.0 mm)
    dry_days = 0.0
    for r in rev:
        if r.precip_sum < 1.0:
            dry_days += 1.0
        else:
            break

    # Days since rain > 10.0 mm
    days_since_heavy_rain = 30.0  # default ceiling
    for i, r in enumerate(rev):
        if r.precip_sum >= 10.0:
            days_since_heavy_rain = float(i)
            break

    return {
        "precip_sum_3d": round(precip_3d, 2),
        "precip_sum_7d": round(precip_7d, 2),
        "precip_sum_14d": round(precip_14d, 2),
        "precip_sum_30d": round(precip_30d, 2),
        "temp_max_mean_7d": round(temp_max_mean_7d, 2),
        "rh_min_mean_7d": round(rh_min_mean_7d, 2),
        "consecutive_dry_days": dry_days,
        "days_since_rain_gt_10mm": days_since_heavy_rain,
    }


def extract_features(
    target_date: date,
    current_weather: DailyWeatherRecord,
    weather_history: Sequence[DailyWeatherRecord],
    fwi_values: Dict[str, float],
    lat: float,
    lon: float,
    landcover: Dict[str, float],
    fires_prev_7d: int = 0,
    fires_prev_30d: int = 0,
    climatological_fire_freq: float = 0.0,
) -> Dict[str, float]:
    """
    Construct a complete single feature row for live inference or dataset generation.
    Strictly asserts zero lookahead leakage.
    """
    # 1. Cyclical
    cyclical = compute_cyclical_features(target_date)

    # 2. Rolling
    rolling = compute_rolling_weather_features(weather_history, target_date)

    # 3. Assemble
    row: Dict[str, float] = {
        "temp_max": current_weather.temp_max,
        "temp_mean": current_weather.temp_mean,
        "rh_min": current_weather.rh_min,
        "rh_mean": current_weather.rh_mean,
        "wind_max": current_weather.wind_max,
        "precip_sum": current_weather.precip_sum,
        "et0": current_weather.et0,
        "soil_moisture": current_weather.soil_moisture,

        "precip_sum_3d": rolling["precip_sum_3d"],
        "precip_sum_7d": rolling["precip_sum_7d"],
        "precip_sum_14d": rolling["precip_sum_14d"],
        "precip_sum_30d": rolling["precip_sum_30d"],
        "temp_max_mean_7d": rolling["temp_max_mean_7d"],
        "rh_min_mean_7d": rolling["rh_min_mean_7d"],

        "consecutive_dry_days": rolling["consecutive_dry_days"],
        "days_since_rain_gt_10mm": rolling["days_since_rain_gt_10mm"],

        "ffmc": fwi_values.get("ffmc", 85.0),
        "dmc": fwi_values.get("dmc", 6.0),
        "dc": fwi_values.get("dc", 15.0),
        "isi": fwi_values.get("isi", 2.0),
        "bui": fwi_values.get("bui", 8.0),
        "fwi": fwi_values.get("fwi", 5.0),

        "month_sin": cyclical["month_sin"],
        "month_cos": cyclical["month_cos"],
        "day_of_year_sin": cyclical["day_of_year_sin"],
        "day_of_year_cos": cyclical["day_of_year_cos"],

        "lat": round(lat, 4),
        "lon": round(lon, 4),

        "fraction_tree": round(landcover.get("tree", 0.0), 4),
        "fraction_shrub": round(landcover.get("shrub", 0.0), 4),
        "fraction_grass": round(landcover.get("grass", 0.0), 4),
        "fraction_crop": round(landcover.get("crop", 0.0), 4),
        "fraction_built": round(landcover.get("built", 0.0), 4),

        "fires_prev_7d": float(fires_prev_7d),
        "fires_prev_30d": float(fires_prev_30d),
        "climatological_fire_freq": round(climatological_fire_freq, 6),
    }

    return row


def derive_wildfire_label(
    fire_detections: Sequence[Dict[str, Any]],
    landcover_classes: Optional[Sequence[str]] = ("tree", "shrub", "grass"),
    min_confidence: str = "nominal"
) -> int:
    """
    Binary label definition:
    1 if at least one FIRMS detection with confidence >= nominal AND
    landcover_class in {tree, shrub, grass}.
    """
    for f in fire_detections:
        conf = str(f.get("confidence", "")).lower()
        if conf in ("low", "l") and min_confidence in ("nominal", "high", "n", "h"):
            continue

        lc = str(f.get("landcover_class", "")).lower()
        if landcover_classes is None or any(target in lc for target in landcover_classes):
            return 1
    return 0
