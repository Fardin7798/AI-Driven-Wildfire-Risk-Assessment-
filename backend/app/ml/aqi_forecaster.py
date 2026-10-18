from datetime import date, timedelta
from typing import Any

from app.domain.aqi import calculate_cpcb_aqi


def forecast_aqi_trajectory(
    target_date: date,
    current_aqi: int,
    current_pm25: float | None = None,
    current_pm10: float | None = None,
    weather_forecast: list[dict[str, Any]] | None = None,
    model_version: str = "aqi_persistence_v1",
) -> list[dict[str, Any]]:
    """
    Generate 1 to 3 day AQI trajectory forecasts using persistence baseline
    with meteorological dispersion adjustments (wind dispersion, rain washout).
    """
    forecasts: list[dict[str, Any]] = []
    base_pm25 = current_pm25 if current_pm25 is not None else float(current_aqi * 0.7)
    base_pm10 = current_pm10 if current_pm10 is not None else float(current_aqi * 1.2)

    for horizon in range(1, 4):
        future_date = target_date + timedelta(days=horizon)
        dispersion_factor = 1.0

        # Meteorological adjustments if weather forecast available
        if weather_forecast and len(weather_forecast) >= horizon:
            w = weather_forecast[horizon - 1]
            wind = float(w.get("wind_max", 10.0))
            rain = float(w.get("precip_sum", 0.0))

            # Wind > 15 km/h improves dispersion
            if wind > 15.0:
                dispersion_factor -= min(0.3, (wind - 15.0) * 0.015)
            # Rain > 2 mm washes out particulates
            if rain > 2.0:
                dispersion_factor -= min(0.4, (rain / 20.0) * 0.3)

        pred_pm25 = max(5.0, round(base_pm25 * dispersion_factor, 1))
        pred_pm10 = max(10.0, round(base_pm10 * dispersion_factor, 1))

        calc = calculate_cpcb_aqi({"pm25": pred_pm25, "pm10": pred_pm10})

        forecasts.append(
            {
                "target_date": future_date.isoformat(),
                "horizon_days": horizon,
                "pm25_pred": pred_pm25,
                "aqi_pred": calc.aqi,
                "aqi_category": calc.category,
                "model_version": model_version,
            }
        )

    return forecasts
