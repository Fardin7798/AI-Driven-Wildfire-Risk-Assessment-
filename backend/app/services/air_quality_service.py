from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.air_quality import AQForecast, AQObservation
from app.providers.base import RawAQObservation


async def get_latest_air_quality(
    session: AsyncSession, state: str | None = None, limit: int = 50
) -> list[AQObservation]:
    query = select(AQObservation).order_by(AQObservation.observed_at_utc.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_air_quality_for_region(session: AsyncSession, region_id: int) -> AQObservation | None:
    query = (
        select(AQObservation)
        .where(AQObservation.region_id == region_id)
        .order_by(AQObservation.observed_at_utc.desc())
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_air_quality_forecast(session: AsyncSession, region_id: int) -> list[AQForecast]:
    today = date.today()
    query = (
        select(AQForecast)
        .where(AQForecast.region_id == region_id, AQForecast.target_date >= today)
        .order_by(AQForecast.target_date.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def upsert_aq_observation(
    session: AsyncSession,
    obs: RawAQObservation,
    region_id: int | None = None,
    station_id: int | None = None,
) -> None:
    stmt = (
        insert(AQObservation)
        .values(
            station_id=station_id,
            region_id=region_id,
            observed_at_utc=obs.observed_at_utc,
            pm25=obs.pm25,
            pm10=obs.pm10,
            no2=obs.no2,
            so2=obs.so2,
            co=obs.co,
            o3=obs.o3,
            nh3=obs.nh3,
            aqi=obs.aqi,
            aqi_category=obs.aqi_category,
            provider=obs.provider,
        )
        .on_conflict_do_update(
            index_elements=["provider", "station_id", "region_id", "observed_at_utc"],
            set_={
                "pm25": obs.pm25,
                "pm10": obs.pm10,
                "no2": obs.no2,
                "so2": obs.so2,
                "co": obs.co,
                "o3": obs.o3,
                "nh3": obs.nh3,
                "aqi": obs.aqi,
                "aqi_category": obs.aqi_category,
            },
        )
    )
    await session.execute(stmt)
