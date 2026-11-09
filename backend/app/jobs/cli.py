"""Run pipeline jobs from the command line: `python -m app.jobs.cli <job> [<job> ...]`.

Used by .github/workflows/pipeline-jobs.yml. The Open-Meteo jobs (ingest_weather, forecast_aqi)
run there instead of on Render because Render's shared outbound IP uses up Open-Meteo's free daily
quota (forecast_aqi failed on 2026-11-03 and 2026-11-04 with "Daily API request limit exceeded").
The FWI -> risk chain runs in the same workflow job right after weather so each step reads the
previous step's output. Jobs run in the order given; the first failure stops the run with exit
code 1 (each job records its own wf.ingestion_runs row through tracked_job).
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.api.v1.internal_jobs import JOB_MAPPING
from app.db.models.ingestion import IngestionRun
from app.db.session import async_session_factory

SKIP_FLAG = "--unless-succeeded-within="


async def _succeeded_within(job_name: str, hours: float) -> bool:
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with async_session_factory() as session:
        row = await session.execute(
            select(IngestionRun.id)
            .where(
                IngestionRun.job_name == job_name,
                IngestionRun.status == "success",
                IngestionRun.started_at >= since,
            )
            .limit(1)
        )
        return row.first() is not None


async def _run(names: list[str]) -> int:
    hours: float | None = None
    if names and names[0].startswith(SKIP_FLAG):
        # A retry or a late GitHub cron run: skip each job that already succeeded recently
        # (e.g. Render dispatched it on time), so Open-Meteo quota is not spent twice. The check
        # is per job: a skipped ingest_weather must not stop update_fwi_state / predict_risk
        # (on 2026-11-09 the whole chain was skipped that way and risk stayed on 11-08).
        hours = float(names[0][len(SKIP_FLAG) :])
        names = names[1:]
    for name in names:
        handler = JOB_MAPPING.get(name)
        if handler is None:
            print(f"unknown job {name!r}; valid: {sorted(JOB_MAPPING)}", file=sys.stderr)
            return 2
        if hours is not None and await _succeeded_within(name, hours):
            print(f"{name}: succeeded within {hours:g} h; skipped")
            continue
        try:
            rows = await handler()
        except Exception as e:  # recorded as failed by tracked_job; stop the chain
            print(f"{name}: FAILED: {str(e)[:500]}", file=sys.stderr)
            return 1
        print(f"{name}: ok, rows_written={rows}")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(
            f"usage: python -m app.jobs.cli [{SKIP_FLAG}HOURS] <job> [<job> ...]", file=sys.stderr
        )
        raise SystemExit(2)
    raise SystemExit(asyncio.run(_run(sys.argv[1:])))


if __name__ == "__main__":
    main()
