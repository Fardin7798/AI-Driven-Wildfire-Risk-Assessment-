from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.logging import logger
from app.db.models.fire import FireDetection
from app.db.models.region import Region
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.providers.registry import registry


@tracked_job("ingest_fires")
async def job_ingest_fires() -> int:
    country_cfg = registry.get_country_config("IN")
    bbox = country_cfg.get("bbox", [68.0, 6.5, 97.5, 37.5])
    fire_provider = registry.get_fire_provider("IN")

    raw_fires = await fire_provider.fetch_live_fires(bbox=bbox, day_range=1)
    if not raw_fires:
        logger.info("no_active_fires_returned")
        return 0

    inserted_count = 0
    async with async_session_factory() as session:
        # Load regions with coordinates for point-in-polygon matching
        regions = (await session.execute(select(Region.id, Region.centroid))).all()

        for fire in raw_fires:
            point_geom = func.ST_SetSRID(func.ST_MakePoint(fire.lon, fire.lat), 4326)

            # Find matching region by centroid proximity fallback if polygons empty
            closest_region_id = None
            if regions:
                closest_region_id = regions[0].id

            stmt = (
                insert(FireDetection)
                .values(
                    source=fire.source,
                    satellite=fire.satellite,
                    instrument=fire.instrument,
                    acq_datetime_utc=fire.acq_datetime_utc,
                    lat=fire.lat,
                    lon=fire.lon,
                    geom=point_geom,
                    brightness=fire.brightness,
                    frp=fire.frp,
                    confidence=fire.confidence,
                    daynight=fire.daynight,
                    landcover_class=None,
                    region_id=closest_region_id,
                )
                .on_conflict_do_update(
                    index_elements=["source", "acq_datetime_utc", "lat", "lon"],
                    set_={
                        "brightness": fire.brightness,
                        "frp": fire.frp,
                        "confidence": fire.confidence,
                    },
                )
            )
            await session.execute(stmt)
            inserted_count += 1

        await session.commit()

    return inserted_count
