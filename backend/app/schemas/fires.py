from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.names import ReadableName


class FireDetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    satellite: str
    instrument: str
    acq_datetime_utc: datetime
    lat: float
    lon: float
    brightness: float | None = None
    frp: float | None = None
    confidence: str | None = None
    daynight: str | None = None
    landcover_class: str | None = None
    region_id: int | None = None
    state_name: ReadableName | None = None
    district_name: ReadableName | None = None


class FireStatsResponse(BaseModel):
    period_days: int = 7
    total_detections: int = 0
    high_confidence_count: int = 0
    total_radiative_power_mw: float = 0.0
    total_fires: int = 0
    high_confidence_fires: int = 0
    # Detections whose point falls outside every district polygon (sea, border areas)
    outside_districts: int = 0
    by_source: dict[str, int] = Field(default_factory=dict)
    by_state: dict[str, int] = Field(default_factory=dict)
    time_range_hours: int = 168
