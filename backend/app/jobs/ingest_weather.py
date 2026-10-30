from sqlalchemy import func, select

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
        # Load regions to ingest weather with their centroid coordinates
        query = (
            select(
                Region.id,
                func.ST_Y(Region.centroid).label("lat"),
                func.ST_X(Region.centroid).label("lon"),
            )
            .where(Region.centroid.isnot(None))
            .order_by(Region.id.asc())
        )
        regions = (await session.execute(query)).all()

        for region in regions:
            if region.lat is None or region.lon is None:
                continue
            lat, lon = float(region.lat), float(region.lon)
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
