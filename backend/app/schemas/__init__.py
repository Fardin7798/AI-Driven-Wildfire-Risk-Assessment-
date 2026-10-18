"""Pydantic schemas for request validation and response serialization."""

from app.schemas.air_quality import AQForecastResponse, AQObservationResponse
from app.schemas.common import SHORT_DISCLAIMER, AsOfInfo, PaginatedResponse, get_as_of
from app.schemas.fires import FireDetectionResponse, FireStatsResponse
from app.schemas.jobs import JobTriggerResponse
from app.schemas.meta import DisclaimerResponse, SourceAttribution, SourcesMetaResponse
from app.schemas.models_info import ModelComparisonResponse, ModelVersionResponse
from app.schemas.preparedness import PreparednessItemResponse
from app.schemas.regions import RegionDetail, RegionSummary
from app.schemas.risk import (
    RiskMapFeature,
    RiskMapFeatureProperties,
    RiskMapResponse,
    RiskPredictionResponse,
    TopFactor,
)
from app.schemas.weather import WeatherDailyResponse

__all__ = [
    "AQForecastResponse",
    "AQObservationResponse",
    "AsOfInfo",
    "DisclaimerResponse",
    "FireDetectionResponse",
    "FireStatsResponse",
    "JobTriggerResponse",
    "ModelComparisonResponse",
    "ModelVersionResponse",
    "PaginatedResponse",
    "PreparednessItemResponse",
    "RegionDetail",
    "RegionSummary",
    "RiskMapFeature",
    "RiskMapFeatureProperties",
    "RiskMapResponse",
    "RiskPredictionResponse",
    "SHORT_DISCLAIMER",
    "SourceAttribution",
    "SourcesMetaResponse",
    "TopFactor",
    "WeatherDailyResponse",
    "get_as_of",
]
