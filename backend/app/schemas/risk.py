from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.names import ReadableName


class TopFactor(BaseModel):
    feature: str
    label: str | None = None
    value: float | None = None
    unit: str | None = None
    # TreeSHAP contribution (log-odds) for model predictions; None for FWI-fallback factors
    impact: float | None = None
    method: str | None = None


class RiskPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int
    district_name: ReadableName
    state_name: ReadableName
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
    district_name: ReadableName
    state_name: ReadableName
    date: str = ""
    probability: float | None = None
    risk_class: str | None = None
    fwi_value: float | None = None
    model_version: str | None = None
    has_prediction: bool = True


class RiskMapFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any] | None = None
    properties: RiskMapFeatureProperties


class RiskMapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[RiskMapFeature]
    date: str = ""
    total: int | None = None
    with_prediction: int | None = None
    as_of: dict[str, str]
    disclaimer_short: str
