from app.db.base import Base
from app.db.models.air_quality import AQForecast, AQObservation, AQStation
from app.db.models.fire import FireDetection
from app.db.models.ingestion import IngestionRun
from app.db.models.model_registry import ModelVersion
from app.db.models.preparedness import PreparednessItem
from app.db.models.region import Region
from app.db.models.risk import RiskPrediction
from app.db.models.weather import FWIState, WeatherDaily

__all__ = [
    "Base",
    "Region",
    "FireDetection",
    "WeatherDaily",
    "FWIState",
    "AQStation",
    "AQObservation",
    "AQForecast",
    "RiskPrediction",
    "ModelVersion",
    "IngestionRun",
    "PreparednessItem",
]
