from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.logging import logger
from app.core.timeutil import today_ist
from app.db.models.region import Region
from app.db.models.weather import FWIState, WeatherDaily
from app.db.session import async_session_factory
from app.domain.fwi import FWI_MAX_CARRYOVER_GAP_DAYS, FWI_STARTUP, calculate_daily_fwi, fwi_inputs
from app.jobs.scheduler import tracked_job


@tracked_job("update_fwi_state")
async def job_update_fwi_state() -> int:
    today = today_ist()
    gap_start = today - timedelta(days=FWI_MAX_CARRYOVER_GAP_DAYS)
    updated_count = 0
    skipped_no_weather = 0

    async with async_session_factory() as session:
        region_ids = (await session.execute(select(Region.id))).scalars().all()

        prev_rows = (
            (
                await session.execute(
                    select(FWIState)
                    .where(FWIState.date >= gap_start, FWIState.date < today)
                    .order_by(FWIState.region_id, FWIState.date.asc())
                )
            )
            .scalars()
            .all()
        )
        latest_prev: dict[int, FWIState] = {r.region_id: r for r in prev_rows}  # last wins

        weather_rows = (
            (await session.execute(select(WeatherDaily).where(WeatherDaily.date == today)))
            .scalars()
            .all()
        )
        weather_today: dict[int, WeatherDaily] = {}
        for row in weather_rows:
            # prefer observed/past-day rows over forecast rows for the same date
            if row.region_id not in weather_today or not row.is_forecast:
                weather_today[row.region_id] = row

        for region_id in region_ids:
            w = weather_today.get(region_id)
            inputs = fwi_inputs(w.temp_max, w.rh_mean, w.wind_max, w.precip_sum) if w else None
            if inputs is None:
                skipped_no_weather += 1
                continue

            prev = latest_prev.get(region_id)
            res = calculate_daily_fwi(
                month=today.month,
                prev_ffmc=prev.ffmc if prev else FWI_STARTUP["ffmc"],
                prev_dmc=prev.dmc if prev else FWI_STARTUP["dmc"],
                prev_dc=prev.dc if prev else FWI_STARTUP["dc"],
                **inputs,
            )
            values = {
                "ffmc": res.ffmc,
                "dmc": res.dmc,
                "dc": res.dc,
                "isi": res.isi,
                "bui": res.bui,
                "fwi": res.fwi,
            }
            stmt = (
                insert(FWIState)
                .values(region_id=region_id, date=today, **values)
                .on_conflict_do_update(index_elements=["region_id", "date"], set_=values)
            )
            await session.execute(stmt)
            updated_count += 1

        await session.commit()

    if skipped_no_weather:
        logger.warn(
            "fwi_regions_skipped_missing_weather", count=skipped_no_weather, date=str(today)
        )
    if updated_count == 0:
        raise RuntimeError(
            "FWI update wrote 0 rows: no weather for today (run ingest_weather first)"
        )
    return updated_count
