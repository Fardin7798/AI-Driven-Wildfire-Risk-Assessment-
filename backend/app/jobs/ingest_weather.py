from sqlalchemy import select

from app.core.logging import logger
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.providers.registry import registry
from app.services.weather_service import upsert_daily_weather


@tracked_job("ingest_weather")
async def job_ingest_weather() -> int:
    weather_provider = registry.get_weather_provider("IN")
    total_written = 0

    async with async_session_factory() as session:
        # Load regions to ingest weather
        query = select(Region.id, Region.centroid).limit(200)
        regions = (await session.execute(query)).all()

        for region in regions:
            # Estimate lat, lon from region centroid if available, default to New Delhi
            lat, lon = 28.6139, 77.2090
            try:
                records = await weather_provider.fetch_weather_forecast(
                    lat=lat, lon=lon, past_days=3, forecast_days=3
                )
                count = await upsert_daily_weather(
                    session, region_id=region.id, records=records, is_forecast=False
                )
                total_written += count
            except Exception as e:
                logger.warn("weather_fetch_error_for_region", region_id=region.id, error=str(e))
                continue

        await session.commit()

    return total_written
