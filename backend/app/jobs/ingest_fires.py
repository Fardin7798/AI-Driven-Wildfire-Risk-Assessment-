from datetime import date

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from app.core.logging import logger
from app.db.models.fire import FireDetection
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job
from app.providers.registry import registry


@tracked_job("ingest_fires")
async def job_ingest_fires() -> int:
    """Daily job: the last 24 h of detections."""
    return await ingest_fire_window(day_range=1)


async def ingest_fire_window(day_range: int = 1, start_date: date | None = None) -> int:
    """Fetch FIRMS detections for a window, upsert them and map them to districts."""
    country_cfg = registry.get_country_config("IN")
    bbox = country_cfg.get("bbox", [68.0, 6.5, 97.5, 37.5])
    fire_provider = registry.get_fire_provider("IN")

    raw_fires = await fire_provider.fetch_live_fires(
        bbox=bbox, day_range=day_range, start_date=start_date
    )
    if not raw_fires:
        logger.info("no_active_fires_returned")
        return 0

    inserted_count = 0
    batch_size = 200
    async with async_session_factory() as session:
        for i in range(0, len(raw_fires), batch_size):
            chunk = raw_fires[i : i + batch_size]
            values = [
                {
                    "source": fire.source,
                    "satellite": fire.satellite,
                    "instrument": fire.instrument,
                    "acq_datetime_utc": fire.acq_datetime_utc,
                    "lat": fire.lat,
                    "lon": fire.lon,
                    "geom": func.ST_SetSRID(func.ST_MakePoint(fire.lon, fire.lat), 4326),
                    "brightness": fire.brightness,
                    "frp": fire.frp,
                    "confidence": fire.confidence,
                    "daynight": fire.daynight,
                    "landcover_class": None,
                    "region_id": None,
                }
                for fire in chunk
            ]
            stmt = (
                insert(FireDetection)
                .values(values)
                .on_conflict_do_nothing(
                    index_elements=["source", "acq_datetime_utc", "lat", "lon"],
                )
            )
            await session.execute(stmt)
            inserted_count += len(chunk)

        # Spatially map fires to their true district boundaries via PostGIS
        await session.execute(
            text("""
            UPDATE wf.fire_detections f
            SET region_id = r.id
            FROM wf.regions r
            WHERE f.region_id IS NULL
              AND ST_Contains(r.geom, f.geom)
            """)
        )
        await session.commit()

    return inserted_count
