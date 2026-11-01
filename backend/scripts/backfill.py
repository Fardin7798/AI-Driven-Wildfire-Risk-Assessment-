"""Backfill FIRMS fire detections for the last N days.

The wildfire model uses fires_prev_7d / fires_prev_30d, read from wf.fire_detections.
Run once after deploying the model on a database with no fire history:

    python scripts/backfill.py --days 35
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from app.core.logging import logger
from app.jobs.ingest_fires import ingest_fire_window

FIRMS_MAX_DAYS_PER_REQUEST = 5


async def backfill_fires(days: int) -> int:
    today = datetime.now(UTC).date()
    start = today - timedelta(days=days - 1)
    total = 0
    while start <= today:
        span = min(FIRMS_MAX_DAYS_PER_REQUEST, (today - start).days + 1)
        rows = await ingest_fire_window(day_range=span, start_date=start)
        logger.info("fire_backfill_window", start=start.isoformat(), days=span, rows=rows)
        total += rows
        start += timedelta(days=span)
    logger.info("fire_backfill_completed", days=days, rows=total)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill FIRMS fire detections")
    parser.add_argument("--days", type=int, default=35, help="days to backfill (max ~60 for NRT)")
    args = parser.parse_args()
    asyncio.run(backfill_fires(args.days))


if __name__ == "__main__":
    main()
