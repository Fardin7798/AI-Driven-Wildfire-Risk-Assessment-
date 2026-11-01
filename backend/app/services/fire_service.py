from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fire import FireDetection
from app.db.models.region import Region
from app.domain.names import humanize_gadm_name


async def get_recent_fires(
    session: AsyncSession, hours: int = 24, bbox: Sequence[float] | None = None, limit: int = 1000
) -> list[FireDetection]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    query = select(FireDetection).where(FireDetection.acq_datetime_utc >= cutoff)

    if bbox and len(bbox) == 4:
        west, south, east, north = bbox
        query = query.where(
            FireDetection.lon >= west,
            FireDetection.lon <= east,
            FireDetection.lat >= south,
            FireDetection.lat <= north,
        )

    query = query.order_by(FireDetection.acq_datetime_utc.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_fire_stats(session: AsyncSession, days: int = 7) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=days)

    total_query = select(func.count(FireDetection.id)).where(
        FireDetection.acq_datetime_utc >= cutoff
    )
    total_count = (await session.execute(total_query)).scalar() or 0

    frp_query = select(func.coalesce(func.sum(FireDetection.frp), 0.0)).where(
        FireDetection.acq_datetime_utc >= cutoff
    )
    total_frp = (await session.execute(frp_query)).scalar() or 0.0

    high_conf_query = select(func.count(FireDetection.id)).where(
        FireDetection.acq_datetime_utc >= cutoff,
        func.lower(FireDetection.confidence).in_(["high", "h"]),
    )
    high_conf_count = (await session.execute(high_conf_query)).scalar() or 0

    by_source_q = (
        select(FireDetection.source, func.count(FireDetection.id))
        .where(FireDetection.acq_datetime_utc >= cutoff)
        .group_by(FireDetection.source)
    )
    by_source = {str(k): int(v) for k, v in (await session.execute(by_source_q)).all()}

    by_state_q = (
        select(Region.state_name, func.count(FireDetection.id))
        .join(Region, FireDetection.region_id == Region.id)
        .where(FireDetection.acq_datetime_utc >= cutoff)
        .group_by(Region.state_name)
        .order_by(func.count(FireDetection.id).desc())
    )
    by_state = {
        humanize_gadm_name(k) or str(k): int(v)
        for k, v in (await session.execute(by_state_q)).all()
    }

    return {
        "period_days": days,
        "total_detections": total_count,
        "high_confidence_count": high_conf_count,
        "total_radiative_power_mw": round(float(total_frp), 2),
        "by_source": by_source,
        "by_state": by_state,
        "outside_districts": total_count - sum(by_state.values()),
    }


async def get_fires_near_coords(
    session: AsyncSession, lat: float, lon: float, radius_km: float = 50.0, hours: int = 48
) -> list[FireDetection]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    # 1 degree latitude ~ 111 km. 50 km buffer ~ 0.45 degrees
    deg_delta = radius_km / 111.0

    query = (
        select(FireDetection)
        .where(
            FireDetection.acq_datetime_utc >= cutoff,
            FireDetection.lat >= (lat - deg_delta),
            FireDetection.lat <= (lat + deg_delta),
            FireDetection.lon >= (lon - deg_delta),
            FireDetection.lon <= (lon + deg_delta),
        )
        .order_by(FireDetection.acq_datetime_utc.desc())
        .limit(100)
    )
    result = await session.execute(query)
    return list(result.scalars().all())
