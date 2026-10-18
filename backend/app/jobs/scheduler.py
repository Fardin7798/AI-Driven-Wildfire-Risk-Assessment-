import functools
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import logger
from app.db.models.ingestion import IngestionRun
from app.db.session import async_session_factory, engine

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
ADVISORY_LOCK_ID = 882199042


def tracked_job(job_name: str):
    """Decorator to ensure every job records an ingestion_run row and respects locking."""

    def decorator(func: Callable[[], Coroutine[Any, Any, int]]):
        @functools.wraps(func)
        async def wrapper() -> int:
            rows_written = 0
            try:
                async with engine.connect() as conn:
                    try:
                        res = await conn.execute(
                            text(f"SELECT pg_try_advisory_lock({ADVISORY_LOCK_ID});")
                        )
                        has_lock = bool(res.scalar())
                    except Exception as lock_err:
                        logger.warn(
                            "advisory_lock_error_skipping_job", job=job_name, error=str(lock_err)
                        )
                        return 0

                    if not has_lock:
                        logger.info("job_skipped_lock_held_by_another_worker", job=job_name)
                        return 0

                    run_id: int | None = None
                    err_msg: str | None = None

                    async with async_session_factory() as session:
                        run_entry = IngestionRun(
                            job_name=job_name,
                            started_at=datetime.now(UTC),
                            status="running",
                            rows_written=0,
                        )
                        session.add(run_entry)
                        await session.commit()
                        run_id = run_entry.id

                    try:
                        logger.info("job_started", job=job_name)
                        rows_written = await func()
                        status_str = "success"
                        logger.info("job_finished_successfully", job=job_name, rows=rows_written)
                    except Exception as e:
                        status_str = "failed"
                        err_str = str(e)[:500]
                        if settings.FIRMS_MAP_KEY:
                            err_str = err_str.replace(settings.FIRMS_MAP_KEY, "***")
                        if settings.JOB_TOKEN:
                            err_str = err_str.replace(settings.JOB_TOKEN, "***")
                        if settings.DATAGOVIN_API_KEY:
                            err_str = err_str.replace(settings.DATAGOVIN_API_KEY, "***")
                        err_msg = err_str
                        logger.error("job_failed", job=job_name, error=err_msg)
                    finally:
                        if run_id:
                            async with async_session_factory() as session:
                                update_entry = await session.get(IngestionRun, run_id)
                                if update_entry:
                                    update_entry.finished_at = datetime.now(UTC)
                                    update_entry.status = status_str
                                    update_entry.rows_written = rows_written
                                    update_entry.error = err_msg
                                    await session.commit()
                        try:
                            await conn.execute(
                                text(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_ID});")
                            )
                            await conn.commit()
                        except Exception as unlock_err:
                            logger.warn("advisory_unlock_error", error=str(unlock_err))
            except Exception as outer_err:
                logger.error("job_connection_error", job=job_name, error=str(outer_err))
                return 0

            return rows_written

        return wrapper

    return decorator


def start_scheduler() -> None:
    """Initialize in-process APScheduler with scheduled intervals."""
    if not settings.ENABLE_SCHEDULER:
        logger.info("scheduler_disabled_by_config")
        return

    from app.jobs.forecast_aqi import job_forecast_aqi
    from app.jobs.ingest_air_quality import job_ingest_air_quality
    from app.jobs.ingest_fires import job_ingest_fires
    from app.jobs.ingest_weather import job_ingest_weather
    from app.jobs.predict_risk import job_predict_risk
    from app.jobs.retention import job_retention
    from app.jobs.update_fwi_state import job_update_fwi_state

    # 1. Fires: Every 3 hours
    scheduler.add_job(
        job_ingest_fires, "interval", hours=3, id="job_ingest_fires", replace_existing=True
    )

    # 2. Weather: Daily at 00:30 IST (19:00 UTC)
    scheduler.add_job(
        job_ingest_weather,
        "cron",
        hour=0,
        minute=0,
        id="job_ingest_weather",
        replace_existing=True,
    )

    # 3. FWI State: Daily after weather at 00:45 IST (19:15 UTC)
    scheduler.add_job(
        job_update_fwi_state,
        "cron",
        hour=0,
        minute=45,
        id="job_update_fwi_state",
        replace_existing=True,
    )

    # 4. Predict Risk: Daily after FWI at 01:00 IST (19:30 UTC)
    scheduler.add_job(
        job_predict_risk, "cron", hour=0, minute=0, id="job_predict_risk", replace_existing=True
    )

    # 5. Air Quality Ingest: Hourly
    scheduler.add_job(
        job_ingest_air_quality,
        "interval",
        hours=1,
        id="job_ingest_air_quality",
        replace_existing=True,
    )

    # 6. AQ Forecast: Daily at 01:15 IST (19:45 UTC)
    scheduler.add_job(
        job_forecast_aqi, "cron", hour=0, minute=45, id="job_forecast_aqi", replace_existing=True
    )

    # 7. Retention: Weekly on Sunday at 02:00 IST (20:30 UTC Sat)
    scheduler.add_job(
        job_retention,
        "cron",
        day_of_week="sun",
        hour=2,
        minute=0,
        id="job_retention",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("apscheduler_started_successfully")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("apscheduler_shutdown")
