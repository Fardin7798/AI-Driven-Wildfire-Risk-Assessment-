from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TopFactor(BaseModel):
    feature: str
    impact: float


class RiskPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int
    district_name: str
    state_name: str
    date: date
    probability: float
    risk_class: str
    model_version: str
    fwi_value: float | None = None
    top_factors: list[TopFactor] = Field(default_factory=list)
    as_of: dict[str, str]
    disclaimer_short: str


class RiskMapFeatureProperties(BaseModel):
    region_id: int
    district_name: str
    state_name: str
    date: str
    probability: float
    risk_class: str
    fwi_value: float | None = None
    model_version: str


class RiskMapFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: RiskMapFeatureProperties


class RiskMapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[RiskMapFeature]
    date: str
    as_of: dict[str, str]
    disclaimer_short: str
