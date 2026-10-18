from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    model_type: str
    version: str
    trained_at: datetime | None = None
    metrics: dict[str, Any] | None = None
    status: str = "active"
    feature_list: list[str] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class ModelComparisonResponse(BaseModel):
    status: str = "available"
    models: list[dict[str, Any]] = Field(default_factory=list)
    wildfire_comparison: dict[str, Any] | None = None
    aqi_comparison: dict[str, Any] | None = None
    evaluation_criteria: list[str] = Field(default_factory=list)
