import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.domain.features import FEATURE_NAMES


@dataclass
class ModelArtifact:
    model_version: str
    metadata: dict[str, Any]
    feature_list: list[str]
    thresholds: dict[str, float]
    metrics: dict[str, Any]
    model_obj: Any
    is_fallback: bool = False


class ModelLoader:
    def __init__(self, model_dir: str | None = None):
        self.model_dir = model_dir or settings.MODEL_DIR
        self._cache: dict[str, ModelArtifact] = {}

    def _compute_sha256(self, filepath: str) -> str:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()

    def load_wildfire_model(self, version: str | None = None) -> ModelArtifact | None:
        ver = version or settings.ACTIVE_WILDFIRE_MODEL
        if ver in self._cache:
            return self._cache[ver]

        meta_path = os.path.join(self.model_dir, f"{ver}_metadata.json")
        model_path = os.path.join(self.model_dir, f"{ver}.json")

        if not os.path.exists(meta_path) or not os.path.exists(model_path):
            logger.info("wildfire_model_artifact_not_found_fallback_active", version=ver)
            return None

        try:
            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)

            # 1. Verify Checksum
            expected_sha = metadata.get("sha256")
            actual_sha = self._compute_sha256(model_path)
            if expected_sha and expected_sha != actual_sha:
                logger.error(
                    "wildfire_model_checksum_mismatch", expected=expected_sha, actual=actual_sha
                )
                return None

            # 2. Verify Feature List
            model_features = metadata.get("feature_list", [])
            if model_features != FEATURE_NAMES:
                logger.error(
                    "wildfire_model_feature_mismatch", expected=FEATURE_NAMES, got=model_features
                )
                return None

            # 3. Load XGBoost Model Object
            try:
                import xgboost as xgb

                model_obj = xgb.Booster()
                model_obj.load_model(model_path)
            except Exception as xgb_err:
                logger.warn("xgboost_load_failed_using_stub", error=str(xgb_err))
                model_obj = None

            artifact = ModelArtifact(
                model_version=ver,
                metadata=metadata,
                feature_list=model_features,
                thresholds=metadata.get("thresholds", {}),
                metrics=metadata.get("metrics", {}),
                model_obj=model_obj,
                is_fallback=(model_obj is None),
            )
            self._cache[ver] = artifact
            return artifact

        except Exception as e:
            logger.error("wildfire_model_load_error", version=ver, error=str(e))
            return None


model_loader = ModelLoader()
