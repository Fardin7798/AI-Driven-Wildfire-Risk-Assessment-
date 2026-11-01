import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.timeutil import today_ist
from app.db.models.air_quality import AQForecast, AQObservation
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.ml.aqi_forecaster import forecast_aqi_trajectory

logger = logging.getLogger(__name__)

# An observation older than this is not "current" and is not persisted forward.
MAX_OBSERVATION_AGE = timedelta(hours=24)


@tracked_job("forecast_aqi")
async def job_forecast_aqi() -> int:
    today = today_ist()
    cutoff = datetime.now(UTC) - MAX_OBSERVATION_AGE
    total_written = 0
    skipped = 0

    async with async_session_factory() as session:
        regions = (await session.execute(select(Region.id))).scalars().all()

        for region_id in regions:
            obs = (
                await session.execute(
                    select(AQObservation)
                    .where(
                        AQObservation.region_id == region_id,
                        AQObservation.observed_at_utc >= cutoff,
                        AQObservation.aqi.is_not(None),
                    )
                    .order_by(AQObservation.observed_at_utc.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            # Old forecasts are removed either way, so a district never shows a stale forecast.
            await session.execute(
                delete(AQForecast).where(
                    AQForecast.region_id == region_id,
                    AQForecast.target_date >= today,
                )
            )

            items = forecast_aqi_trajectory(
                target_date=today,
                observed_aqi=obs.aqi if obs else None,
                observed_pm25=obs.pm25 if obs else None,
            )
            if not items:
                skipped += 1
                continue

            for item in items:
                await session.execute(
                    insert(AQForecast).values(
                        region_id=region_id,
                        target_date=date.fromisoformat(item["target_date"]),
                        horizon_days=item["horizon_days"],
                        pm25_pred=item["pm25_pred"],
                        aqi_pred=item["aqi_pred"],
                        aqi_category=item["aqi_category"],
                        model_version=item["model_version"],
                    )
                )
                total_written += 1

        await session.commit()

    if skipped:
        logger.warning("forecast_aqi: %d regions without a valid AQI in the last 24 h", skipped)
    return total_written
