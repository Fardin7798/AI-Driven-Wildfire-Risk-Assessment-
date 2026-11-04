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

from app.api.v1.internal_jobs import JOB_MAPPING


async def _run(names: list[str]) -> int:
    for name in names:
        handler = JOB_MAPPING.get(name)
        if handler is None:
            print(f"unknown job {name!r}; valid: {sorted(JOB_MAPPING)}", file=sys.stderr)
            return 2
        try:
            rows = await handler()
        except Exception as e:  # recorded as failed by tracked_job; stop the chain
            print(f"{name}: FAILED: {str(e)[:500]}", file=sys.stderr)
            return 1
        print(f"{name}: ok, rows_written={rows}")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m app.jobs.cli <job> [<job> ...]", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(_run(sys.argv[1:])))


if __name__ == "__main__":
    main()
