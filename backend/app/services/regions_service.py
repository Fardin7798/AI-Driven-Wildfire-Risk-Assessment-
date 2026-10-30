from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.region import Region


async def get_regions(
    session: AsyncSession,
    country: str = "IN",
    state: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Region], int]:
    query = select(Region).where(Region.country_code == country.upper())
    if state:
        query = query.where(func.lower(Region.state_name) == state.lower().strip())
    query = query.order_by(Region.state_name, Region.district_name).limit(limit).offset(offset)
    count_query = select(func.count(Region.id)).where(Region.country_code == country.upper())
    if state:
        count_query = count_query.where(func.lower(Region.state_name) == state.lower().strip())
    total = (await session.execute(count_query)).scalar() or 0
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_region_by_id(session: AsyncSession, region_id: int) -> Region | None:
    query = select(Region).where(Region.id == region_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_region_by_coordinates(session: AsyncSession, lat: float, lon: float) -> Region | None:
    stmt = (
        select(Region)
        .where(
            func.ST_Contains(
                Region.geom,
                func.ST_SetSRID(func.ST_Point(lon, lat), 4326),
            )
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
