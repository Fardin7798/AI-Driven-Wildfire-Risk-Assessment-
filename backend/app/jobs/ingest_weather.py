import asyncio

from sqlalchemy import func, select

from app.core.logging import logger
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.providers.open_meteo_http import BATCH_PAUSE_SECONDS, OpenMeteoQuotaExceeded
from app.providers.open_meteo_weather import OpenMeteoWeatherProvider
from app.providers.registry import registry
from app.services.weather_service import upsert_daily_weather

# Open-Meteo multi-location requests: one HTTP call per batch instead of one per district.
WEATHER_BATCH_SIZE = 50


@tracked_job("ingest_weather")
async def job_ingest_weather() -> int:
    weather_provider = registry.get_weather_provider("IN")
    total_written = 0
    failed_batches = 0

    async with async_session_factory() as session:
        query = (
            select(
                Region.id,
                func.ST_Y(Region.centroid).label("lat"),
                func.ST_X(Region.centroid).label("lon"),
            )
            .where(Region.centroid.isnot(None))
            .order_by(Region.id.asc())
        )
        regions = [r for r in (await session.execute(query)).all() if r.lat is not None]
        if not regions:
            raise RuntimeError("No regions with centroids found; run scripts/load_regions.py first")

        for start in range(0, len(regions), WEATHER_BATCH_SIZE):
            batch = regions[start : start + WEATHER_BATCH_SIZE]
            coords = [(float(r.lat), float(r.lon)) for r in batch]
            try:
                if isinstance(weather_provider, OpenMeteoWeatherProvider):
                    per_region = await weather_provider.fetch_weather_forecast_batch(
                        coords, past_days=3, forecast_days=3
                    )
                else:  # providers without multi-location support
                    per_region = [
                        await weather_provider.fetch_weather_forecast(
                            lat=lat, lon=lon, past_days=3, forecast_days=3
                        )
                        for lat, lon in coords
                    ]
            except OpenMeteoQuotaExceeded as e:
                logger.error("open_meteo_quota_exceeded_stopping", error=str(e))
                break
            except Exception as e:
                failed_batches += 1
                logger.warn(
                    "weather_batch_fetch_error",
                    first_region_id=batch[0].id,
                    size=len(batch),
                    error=str(e),
                )
                continue

            for region, records in zip(batch, per_region, strict=True):
                total_written += await upsert_daily_weather(
                    session, region_id=region.id, records=records, is_forecast=False
                )
            await session.commit()
            await asyncio.sleep(BATCH_PAUSE_SECONDS)

    if total_written == 0:
        raise RuntimeError(f"Weather ingestion wrote 0 rows ({failed_batches} batches failed)")
    return total_written
