import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import async_session_factory

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    db: str = "ok"


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Lightweight operational health probe. Does not leak infrastructure or provider details."""
    db_status = "ok"
    try:
        async with async_session_factory() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1;")), timeout=2.0)
    except Exception:
        db_status = "down"
    return HealthResponse(status="ok", version=settings.APP_VERSION, db=db_status)
