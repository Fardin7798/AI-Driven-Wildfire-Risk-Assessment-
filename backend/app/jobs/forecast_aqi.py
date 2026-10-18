from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.timeutil import today_ist
from app.db.models.air_quality import AQForecast, AQObservation
from app.db.models.region import Region
from app.db.models.weather import WeatherDaily
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.ml.aqi_forecaster import forecast_aqi_trajectory


@tracked_job("forecast_aqi")
async def job_forecast_aqi() -> int:
    today = today_ist()
    total_written = 0

    async with async_session_factory() as session:
        regions = (await session.execute(select(Region.id))).scalars().all()

        for region_id in regions:
            # 1. Fetch current AQ observation
            obs_query = (
                select(AQObservation)
                .where(AQObservation.region_id == region_id)
                .order_by(AQObservation.observed_at_utc.desc())
                .limit(1)
            )
            obs = (await session.execute(obs_query)).scalar_one_or_none()

            current_aqi = obs.aqi if (obs and obs.aqi) else 120
            current_pm25 = obs.pm25 if obs else 45.0
            current_pm10 = obs.pm10 if obs else 85.0

            # 2. Fetch weather forecast for days +1, +2, +3
            w_query = (
                select(WeatherDaily)
                .where(WeatherDaily.region_id == region_id, WeatherDaily.date > today)
                .order_by(WeatherDaily.date.asc())
                .limit(3)
            )
            w_rows = (await session.execute(w_query)).scalars().all()
            weather_forecast = [
                {"wind_max": w.wind_max or 10.0, "precip_sum": w.precip_sum or 0.0} for w in w_rows
            ]

            # 3. Predict Trajectory
            forecast_items = forecast_aqi_trajectory(
                target_date=today,
                current_aqi=current_aqi,
                current_pm25=current_pm25,
                current_pm10=current_pm10,
                weather_forecast=weather_forecast,
            )

            for item in forecast_items:
                target_d = date.fromisoformat(item["target_date"])
                stmt = insert(AQForecast).values(
                    region_id=region_id,
                    target_date=target_d,
                    horizon_days=item["horizon_days"],
                    pm25_pred=item["pm25_pred"],
                    aqi_pred=item["aqi_pred"],
                    aqi_category=item["aqi_category"],
                    model_version=item["model_version"],
                )
                await session.execute(stmt)
                total_written += 1

        await session.commit()

    return total_written
