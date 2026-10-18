from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.regions import RegionDetail, RegionSummary
from app.services.regions_service import get_region_by_id, get_regions, search_regions

router = APIRouter(prefix="/regions", tags=["Regions"])


@router.get("", response_model=PaginatedResponse[RegionSummary])
async def list_regions(
    country: str = Query(default="IN", max_length=5),
    state: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RegionSummary]:
    """Retrieve district regions with pagination, filterable by country and state."""
    offset = (page - 1) * page_size
    records, total = await get_regions(
        session=db,
        country=country,
        state=state,
        limit=page_size,
        offset=offset,
    )
    items = [RegionSummary.model_validate(r) for r in records]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
    )


@router.get("/search", response_model=list[RegionSummary])
async def search_districts(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[RegionSummary]:
    """Search districts by prefix or partial name match."""
    records = await search_regions(session=db, query_str=q, limit=limit)
    return [RegionSummary.model_validate(r) for r in records]


@router.get("/{region_id}", response_model=RegionDetail)
async def get_district_detail(
    region_id: int,
    db: AsyncSession = Depends(get_db),
) -> RegionDetail:
    """Get district region metadata including boundary geometry."""
    record = await get_region_by_id(session=db, region_id=region_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} not found.",
        )
    return RegionDetail.model_validate(record)
