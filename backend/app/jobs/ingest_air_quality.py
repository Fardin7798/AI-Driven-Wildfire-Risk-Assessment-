from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.providers.registry import registry
from app.services.air_quality_service import upsert_aq_observation


@tracked_job("ingest_air_quality")
async def job_ingest_air_quality() -> int:
    aq_provider = registry.get_air_quality_provider("IN")
    cpcb_provider = registry.get_cpcb_station_provider()
    total_written = 0

    async with async_session_factory() as session:
        # 1. Ingest CAMS Regional AQ for Region Centroids
        regions = (await session.execute(select(Region.id, Region.centroid).limit(100))).all()
        for reg in regions:
            lat, lon = 28.6139, 77.2090
            try:
                obs_list = await aq_provider.fetch_air_quality(lat=lat, lon=lon)
                for obs in obs_list:
                    await upsert_aq_observation(session, obs, region_id=reg.id)
                    total_written += 1
            except Exception as e:
                logger.warn("aq_fetch_failed_for_region", region_id=reg.id, error=str(e))
                continue

        # 2. Ingest CPCB Real-Time Stations (if feature enabled)
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
