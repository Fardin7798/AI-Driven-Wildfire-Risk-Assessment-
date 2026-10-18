from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'wildfire' | 'aqi'
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    feature_list: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    artifact_path: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
