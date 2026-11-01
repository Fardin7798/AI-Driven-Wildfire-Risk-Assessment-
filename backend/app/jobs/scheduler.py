import functools
import zlib
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
ADVISORY_LOCK_NAMESPACE = 8821  # first key of pg_try_advisory_lock(int, int)


def job_lock_key(job_name: str) -> int:
    """Stable per-job advisory lock key.

    Each job gets its OWN lock so two different jobs never block each other; the lock only
    stops the same job running twice at once (e.g. two Render instances, or a GitHub-Actions
    trigger overlapping the in-process schedule).
    """
    return zlib.crc32(job_name.encode()) & 0x7FFFFFFF


class JobFailedError(RuntimeError):
    """A tracked job ran and failed; the ingestion_runs row holds the details."""


def tracked_job(job_name: str):
    """Decorator to ensure every job records an ingestion_run row and respects locking."""

    def decorator(func: Callable[[], Coroutine[Any, Any, int]]):
        @functools.wraps(func)
        async def wrapper() -> int:
            rows_written = 0
            failure: str | None = None
            lock_key = job_lock_key(job_name)
            try:
                async with engine.connect() as conn:
                    try:
                        res = await conn.execute(
                            text("SELECT pg_try_advisory_lock(:ns, :key)"),
                            {"ns": ADVISORY_LOCK_NAMESPACE, "key": lock_key},
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
                        failure = err_msg
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
                                text("SELECT pg_advisory_unlock(:ns, :key)"),
                                {"ns": ADVISORY_LOCK_NAMESPACE, "key": lock_key},
                            )
                            await conn.commit()
                        except Exception as unlock_err:
                            logger.warn("advisory_unlock_error", error=str(unlock_err))
            except Exception as outer_err:
                logger.error("job_connection_error", job=job_name, error=str(outer_err))
                return 0

            if failure is not None:
                # Surface the failure to manual callers (/internal/jobs) instead of "success, 0".
                raise JobFailedError(f"{job_name}: {failure}")
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

    # Daily chain is staggered so each step reads the previous step's output (all IST):
    #   00:20 weather -> 00:50 FWI -> 01:10 risk prediction -> 01:30 AQ forecast
    jobs: list[tuple[Callable[[], Coroutine[Any, Any, int]], str, dict[str, Any]]] = [
        (job_ingest_fires, "job_ingest_fires", {"hour": "*/3", "minute": 10}),
        (job_ingest_air_quality, "job_ingest_air_quality", {"hour": "*/6", "minute": 40}),
        (job_ingest_weather, "job_ingest_weather", {"hour": 0, "minute": 20}),
        (job_update_fwi_state, "job_update_fwi_state", {"hour": 0, "minute": 50}),
        (job_predict_risk, "job_predict_risk", {"hour": 1, "minute": 10}),
        (job_forecast_aqi, "job_forecast_aqi", {"hour": 1, "minute": 30}),
        (job_retention, "job_retention", {"day_of_week": "sun", "hour": 3, "minute": 0}),
    ]
    for func, job_id, cron in jobs:
        scheduler.add_job(
            func, "cron", id=job_id, replace_existing=True, misfire_grace_time=900, **cron
        )

    scheduler.start()
    logger.info("apscheduler_started_successfully")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("apscheduler_shutdown")
