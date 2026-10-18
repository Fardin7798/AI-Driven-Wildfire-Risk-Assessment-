from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Lightweight operational health probe. Does not leak infrastructure or provider details."""
    return HealthResponse(status="ok", version=settings.APP_VERSION)
