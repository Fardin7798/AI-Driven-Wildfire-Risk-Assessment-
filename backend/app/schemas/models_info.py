from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_type: str
    version: str
    trained_at: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)
    feature_list: list[str] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    is_active: bool


class ModelComparisonResponse(BaseModel):
    wildfire_comparison: dict[str, Any] = Field(default_factory=dict)
    aqi_comparison: dict[str, Any] = Field(default_factory=dict)
    evaluation_criteria: list[str] = Field(default_factory=list)
