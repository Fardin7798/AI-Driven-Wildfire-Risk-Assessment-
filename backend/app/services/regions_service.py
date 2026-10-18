from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.region import Region


async def get_regions(
    session: AsyncSession,
    country: str = "IN",
    state: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Region]:
    query = select(Region).where(Region.country_code == country.upper())
    if state:
        query = query.where(func.lower(Region.state_name) == state.lower().strip())
    query = query.order_by(Region.state_name, Region.district_name).limit(limit).offset(offset)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_region_by_id(session: AsyncSession, region_id: int) -> Region | None:
    query = select(Region).where(Region.id == region_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def search_regions(session: AsyncSession, query_str: str, limit: int = 20) -> list[Region]:
    term = f"%{query_str.lower().strip()}%"
    stmt = (
        select(Region)
        .where(
            or_(
                func.lower(Region.district_name).like(term),
                func.lower(Region.state_name).like(term),
            )
        )
        .order_by(Region.district_name)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
