from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.names import ReadableName


class RegionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country_code: str
    admin_level: int
    state_name: ReadableName
    district_name: ReadableName
    gadm_id: str
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    area_km2: float | None = None
    landcover: dict[str, Any] | None = None
    timezone: str


class RegionDetail(RegionSummary):
    geom: dict[str, Any] | None = None
