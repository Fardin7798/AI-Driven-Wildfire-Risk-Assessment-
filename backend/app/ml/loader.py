import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import logger


@dataclass
class ModelArtifact:
    model_version: str
    metadata: dict[str, Any]
    feature_list: list[str]
    thresholds: dict[str, float]
    metrics: dict[str, Any]
    model_obj: Any
    is_fallback: bool = False


AQI_HORIZONS = (1, 2, 3)


@dataclass
class AqiStationModel:
    """AQI model B: PM2.5 sub-index at t+h (h = 1..3) from district features at day t."""

    model_version: str
    metadata: dict[str, Any]
    feature_list: list[str]
    boosters: dict[int, Any]
    coverage: dict[str, Any]


class ModelLoader:
    def __init__(self, model_dir: str | None = None):
        self.model_dir = model_dir or settings.MODEL_DIR
        self._cache: dict[str, ModelArtifact] = {}
        self._aqi_cache: dict[str, AqiStationModel] = {}

    def _compute_sha256(self, filepath: str) -> str:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()

    def wildfire_model_paths(self, version: str) -> dict[str, str]:
        """`<MODEL_DIR>/<version>/<version>{.json,_metadata.json,_evaluation.json}`."""
        root = os.path.join(self.model_dir, version)
        return {
            "model": os.path.join(root, f"{version}.json"),
            "metadata": os.path.join(root, f"{version}_metadata.json"),
            "evaluation": os.path.join(root, f"{version}_evaluation.json"),
        }

    def load_wildfire_model(self, version: str | None = None) -> ModelArtifact | None:
        """Wildfire booster + metadata from `<MODEL_DIR>/<version>/`.

        The booster must match the metadata sha256, the metadata version must equal the
        directory name, and the booster's feature names (when stored) must equal the metadata
        feature list. Any failure -> None, i.e. predict_risk publishes the FWI fallback only.
        """
        ver = version or settings.ACTIVE_WILDFIRE_MODEL
        if ver in self._cache:
            return self._cache[ver]

        paths = self.wildfire_model_paths(ver)
        meta_path, model_path = paths["metadata"], paths["model"]
        if not os.path.exists(meta_path) or not os.path.exists(model_path):
            logger.error("wildfire_model_artifact_not_found_fallback_active", version=ver)
            return None

        try:
            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)

            if metadata.get("version", ver) != ver:
                logger.error(
                    "wildfire_model_version_mismatch", version=ver, metadata=metadata["version"]
                )
                return None

            expected_sha = metadata.get("sha256")
            actual_sha = self._compute_sha256(model_path)
            if not expected_sha or expected_sha != actual_sha:
                logger.error(
                    "wildfire_model_checksum_mismatch", expected=expected_sha, actual=actual_sha
                )
                return None

            model_features = metadata.get("feature_list") or metadata.get("features", [])
            if not model_features:
                logger.error("wildfire_model_missing_features", version=ver)
                return None

            try:
                import xgboost as xgb

                model_obj = xgb.Booster()
                model_obj.load_model(model_path)
            except Exception as xgb_err:
                logger.error("xgboost_load_failed_fwi_fallback", error=str(xgb_err))
                model_obj = None

            if (
                model_obj is not None
                and model_obj.feature_names is not None
                and list(model_obj.feature_names) != list(model_features)
            ):
                logger.error("wildfire_model_feature_mismatch", version=ver)
                return None

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

    def load_aqi_model(self, version: str | None = None) -> AqiStationModel | None:
        """AQI model B (`<MODEL_DIR>/<version>/`): one no-station booster per horizon, each
        verified against the sha256 in aqi_station_metadata.json, plus coverage.json. Any
        missing file, checksum mismatch or load error -> None (no fallback model)."""
        ver = version or settings.ACTIVE_AQI_MODEL
        if ver in self._aqi_cache:
            return self._aqi_cache[ver]

        root = os.path.join(self.model_dir, ver)
        meta_path = os.path.join(root, "aqi_station_metadata.json")
        cov_path = os.path.join(root, "coverage.json")
        if not os.path.exists(meta_path) or not os.path.exists(cov_path):
            logger.error("aqi_model_artifact_not_found", version=ver, path=root)
            return None

        try:
            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)
            with open(cov_path, encoding="utf-8") as f:
                coverage = json.load(f)
            if metadata.get("version") != ver or coverage.get("model_version") != ver:
                logger.error("aqi_model_version_mismatch", version=ver)
                return None
            features = list(metadata["features"]["no_station"])

            import xgboost as xgb

            boosters: dict[int, Any] = {}
            for h in AQI_HORIZONS:
                spec = metadata["models"][f"no_station_h{h}"]
                path = os.path.join(root, spec["file"])
                actual = self._compute_sha256(path)
                if actual != spec["sha256"]:
                    logger.error(
                        "aqi_model_checksum_mismatch",
                        file=spec["file"],
                        expected=spec["sha256"],
                        actual=actual,
                    )
                    return None
                booster = xgb.Booster()
                booster.load_model(path)
                if booster.feature_names is not None and list(booster.feature_names) != features:
                    logger.error("aqi_model_feature_mismatch", file=spec["file"])
                    return None
                boosters[h] = booster
        except Exception as e:
            logger.error("aqi_model_load_error", version=ver, error=str(e))
            return None

        artifact = AqiStationModel(
            model_version=ver,
            metadata=metadata,
            feature_list=features,
            boosters=boosters,
            coverage=coverage,
        )
        self._aqi_cache[ver] = artifact
        return artifact


model_loader = ModelLoader()
