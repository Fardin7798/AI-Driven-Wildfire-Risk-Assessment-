from datetime import date, timedelta
from typing import Any

from app.domain.aqi import get_aqi_category

PERSISTENCE_VERSION = "aqi_persistence_v1"
HORIZONS = (1, 2, 3)


def forecast_aqi_trajectory(
    target_date: date,
    observed_aqi: int | None,
    observed_pm25: float | None,
) -> list[dict[str, Any]]:
    """Persistence baseline: tomorrow and the next two days repeat the latest observed AQI.

    No adjustment and no default is applied. Without an observed AQI there is no forecast
    (empty list), never an invented value. This is the baseline a learned model must beat.
    """
    if observed_aqi is None:
        return []
    return [
        {
            "target_date": (target_date + timedelta(days=h)).isoformat(),
            "horizon_days": h,
            "pm25_pred": observed_pm25,
            "aqi_pred": observed_aqi,
            "aqi_category": get_aqi_category(observed_aqi),
            "model_version": PERSISTENCE_VERSION,
        }
        for h in HORIZONS
    ]
