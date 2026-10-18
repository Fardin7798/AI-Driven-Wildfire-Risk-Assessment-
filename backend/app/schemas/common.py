from datetime import UTC, datetime, timedelta, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

SHORT_DISCLAIMER = (
    "Academic decision-support tool only; not an official warning. "
    "Consult IMD, CPCB, NDMA, and local authorities."
)

IST_TZ = timezone(timedelta(hours=5, minutes=30))


def get_as_of() -> dict[str, str]:
    now_utc = datetime.now(UTC)
    now_ist = now_utc.astimezone(IST_TZ)
    return {
        "utc": now_utc.isoformat(),
        "ist": now_ist.isoformat(),
    }


class AsOfInfo(BaseModel):
    utc: str
    ist: str


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    items: list[T]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    has_more: bool = False
