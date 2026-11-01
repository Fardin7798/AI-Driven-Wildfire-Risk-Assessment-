"""Backfill FIRMS fire detections for the last N days.

The wildfire model uses fires_prev_7d / fires_prev_30d, read from wf.fire_detections.
Run once on a database with no fire history (or call POST /api/v1/internal/jobs/backfill_fires):

    python scripts/backfill.py --days 35
"""

import argparse
import asyncio

from app.jobs.ingest_fires import BACKFILL_DAYS, backfill_fire_history


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill FIRMS fire detections")
    parser.add_argument("--days", type=int, default=BACKFILL_DAYS, help="days (max ~60 for NRT)")
    args = parser.parse_args()
    asyncio.run(backfill_fire_history(args.days))


if __name__ == "__main__":
    main()
