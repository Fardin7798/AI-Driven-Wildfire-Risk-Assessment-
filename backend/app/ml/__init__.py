from app.ml.loader import ModelArtifact, ModelLoader, model_loader
from app.ml.wildfire_predictor import (
    RiskPredictionResult,
    predict_wildfire_risk,
)

__all__ = [
    "ModelLoader",
    "model_loader",
    "ModelArtifact",
    "predict_wildfire_risk",
    "RiskPredictionResult",
]
