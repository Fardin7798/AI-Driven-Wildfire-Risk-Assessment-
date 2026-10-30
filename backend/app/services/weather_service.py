from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import today_ist
from app.db.models.weather import WeatherDaily
from app.providers.base import RawDailyWeather


async def get_weather_for_region(
    session: AsyncSession, region_id: int, days: int = 7
) -> list[WeatherDaily]:
    start_date = today_ist() - timedelta(days=days)
    query = (
        select(WeatherDaily)
        .where(WeatherDaily.region_id == region_id, WeatherDaily.date >= start_date)
        .order_by(WeatherDaily.date.asc())
    )
    result = await session.execute(query)
    records = list(result.scalars().all())
    if not records:
        fallback_query = (
            select(WeatherDaily)
            .where(WeatherDaily.region_id == region_id)
            .order_by(WeatherDaily.date.desc())
            .limit(days)
        )
        fb_res = await session.execute(fallback_query)
        records = sorted(fb_res.scalars().all(), key=lambda r: r.date)
    return records


async def get_latest_weather_record(session: AsyncSession, region_id: int) -> WeatherDaily | None:
    query = (
        select(WeatherDaily)
        .where(WeatherDaily.region_id == region_id)
        .order_by(WeatherDaily.date.desc())
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def upsert_daily_weather(
    session: AsyncSession,
    region_id: int,
    records: Sequence[RawDailyWeather],
    is_forecast: bool = False,
) -> int:
    if not records:
        return 0

    count = 0
    for r in records:
        stmt = (
            insert(WeatherDaily)
            .values(
                region_id=region_id,
                date=r.record_date,
                is_forecast=is_forecast,
                temp_max=r.temp_max,
                temp_min=r.temp_min,
                temp_mean=r.temp_mean,
                rh_mean=r.rh_mean,
                rh_min=r.rh_min,
                wind_max=r.wind_max,
                precip_sum=r.precip_sum,
                et0=r.et0,
                soil_moisture=r.soil_moisture,
                provider=r.provider,
            )
            .on_conflict_do_update(
                index_elements=["region_id", "date", "is_forecast"],
                set_={
                    "temp_max": r.temp_max,
                    "temp_min": r.temp_min,
                    "temp_mean": r.temp_mean,
                    "rh_mean": r.rh_mean,
                    "rh_min": r.rh_min,
                    "wind_max": r.wind_max,
                    "precip_sum": r.precip_sum,
                    "et0": r.et0,
                    "soil_moisture": r.soil_moisture,
                    "provider": r.provider,
                },
            )
        )
        await session.execute(stmt)
        count += 1

    return count
