from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.core.config import settings
from app.core.logging import logger
from app.db.models.air_quality import AQObservation
from app.db.models.fire import FireDetection
from app.db.session import async_session_factory
from app.jobs.scheduler import tracked_job


@tracked_job("retention")
async def job_retention() -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.RETENTION_DAYS)
    total_purged = 0

    async with async_session_factory() as session:
        # 1. Purge old fire detections
        fire_stmt = delete(FireDetection).where(FireDetection.acq_datetime_utc < cutoff)
        fire_res = await session.execute(fire_stmt)
        total_purged += int(getattr(fire_res, "rowcount", 0) or 0)

        # 2. Purge old AQ observations
        aq_stmt = delete(AQObservation).where(AQObservation.observed_at_utc < cutoff)
        aq_res = await session.execute(aq_stmt)
        total_purged += int(getattr(aq_res, "rowcount", 0) or 0)

        await session.commit()

    logger.info(
        "retention_cleanup_completed",
        purged_rows=total_purged,
        retention_days=settings.RETENTION_DAYS,
    )
    return total_purged
