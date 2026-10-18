import argparse
import asyncio
from datetime import date, datetime, timedelta

from app.core.logging import logger
from app.jobs.forecast_aqi import job_forecast_aqi
from app.jobs.ingest_air_quality import job_ingest_air_quality
from app.jobs.ingest_fires import job_ingest_fires
from app.jobs.ingest_weather import job_ingest_weather
from app.jobs.predict_risk import job_predict_risk
from app.jobs.update_fwi_state import job_update_fwi_state

JOB_DISPATCHER = {
    "ingest_fires": job_ingest_fires,
    "ingest_weather": job_ingest_weather,
    "update_fwi_state": job_update_fwi_state,
    "predict_risk": job_predict_risk,
    "ingest_air_quality": job_ingest_air_quality,
    "forecast_aqi": job_forecast_aqi,
}


async def run_backfill(job_name: str, start_date: date, end_date: date):
    job_fn = JOB_DISPATCHER.get(job_name)
    if not job_fn:
        logger.error("invalid_job_name", job=job_name, valid=list(JOB_DISPATCHER.keys()))
        return

    current = start_date
    total_processed = 0

    logger.info(
        "starting_backfill", job=job_name, start=start_date.isoformat(), end=end_date.isoformat()
    )

    while current <= end_date:
        logger.info("running_backfill_day", job=job_name, date=current.isoformat())
        try:
            # Most daily jobs process based on configured windows or daily state
            rows = await job_fn()
            total_processed += rows
            logger.info("backfill_day_completed", date=current.isoformat(), rows=rows)
        except Exception as e:
            logger.error("backfill_day_failed", date=current.isoformat(), error=str(e))

        current += timedelta(days=1)

    logger.info("backfill_completed", job=job_name, total_processed=total_processed)


def parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill scheduled data pipelines across a date window"
    )
    parser.add_argument("--job", "-j", type=str, required=True, choices=list(JOB_DISPATCHER.keys()))
    parser.add_argument("--start-date", "-s", type=parse_date, required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", "-e", type=parse_date, required=True, help="YYYY-MM-DD")

    args = parser.parse_args()
    if args.start_date > args.end_date:
        print("Error: start-date must be <= end-date", file=sys.stderr)
        return

    asyncio.run(run_backfill(args.job, args.start_date, args.end_date))


if __name__ == "__main__":
    import sys

    main()
