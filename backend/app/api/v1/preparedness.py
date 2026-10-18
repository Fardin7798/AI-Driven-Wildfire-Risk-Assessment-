from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.preparedness import PreparednessItemResponse
from app.services.preparedness_service import get_preparedness_items

router = APIRouter(prefix="/preparedness", tags=["Community Preparedness"])


@router.get("", response_model=list[PreparednessItemResponse])
async def list_preparedness_guidelines(
    hazard: str | None = Query(default=None, pattern=r"^(wildfire|air_quality)$"),
    stage: str | None = Query(default=None, pattern=r"^(before|during|after)$"),
    lang: str = Query(default="en", max_length=10),
    db: AsyncSession = Depends(get_db),
) -> list[PreparednessItemResponse]:
    """Retrieve verified community safety and preparedness guidelines from NDMA public advisories."""
    records = await get_preparedness_items(session=db, hazard=hazard, stage=stage, lang=lang)
    return [PreparednessItemResponse.model_validate(r) for r in records]
