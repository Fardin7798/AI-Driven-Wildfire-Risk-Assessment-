import asyncio

from sqlalchemy import func, select

from app.core.config import settings
from app.core.logging import logger
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.providers.open_meteo_air import OpenMeteoAirProvider
from app.providers.registry import registry
from app.services.air_quality_service import upsert_aq_observation

# One multi-location request per batch keeps us inside Open-Meteo's free-tier limits
# (all districts every 6 hours = ~2,700 location-calls/day instead of 16k+/day hourly).
AQ_BATCH_SIZE = 50
BATCH_PAUSE_SECONDS = 2.0


@tracked_job("ingest_air_quality")
async def job_ingest_air_quality() -> int:
    aq_provider = registry.get_air_quality_provider("IN")
    cpcb_provider = registry.get_cpcb_station_provider()
    total_written = 0

    async with async_session_factory() as session:
        # 1. CAMS modelled AQ for every district centroid
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
        for start in range(0, len(regions), AQ_BATCH_SIZE):
            batch = regions[start : start + AQ_BATCH_SIZE]
            coords = [(float(r.lat), float(r.lon)) for r in batch]
            try:
                if isinstance(aq_provider, OpenMeteoAirProvider):
                    per_region = await aq_provider.fetch_air_quality_batch(coords)
                else:
                    per_region = [
                        await aq_provider.fetch_air_quality(lat=lat, lon=lon) for lat, lon in coords
                    ]
            except Exception as e:
                logger.warn(
                    "aq_batch_fetch_failed",
                    first_region_id=batch[0].id,
                    size=len(batch),
                    error=str(e),
                )
                continue
            for region, obs_list in zip(batch, per_region, strict=True):
                for obs in obs_list:
                    await upsert_aq_observation(session, obs, region_id=region.id)
                    total_written += 1
            await session.commit()
            await asyncio.sleep(BATCH_PAUSE_SECONDS)

        # 2. CPCB real-time stations (if feature enabled)
        if settings.ENABLE_CPCB:
            try:
                cpcb_obs = await cpcb_provider.fetch_station_observations(limit=200)
                for obs in cpcb_obs:
                    await upsert_aq_observation(session, obs, region_id=None)
                    total_written += 1
            except Exception as e:
                logger.warn("cpcb_ingest_failed", error=str(e))

        await session.commit()

    return total_written
