from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"
    __table_args__ = (
        UniqueConstraint(
            "region_id", "date", "model_version", name="uq_risk_predictions_region_date_model"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_class: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fwi_value: Mapped[float] = mapped_column(Float, nullable=False)
    top_factors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    region = relationship("Region", back_populates="risk_predictions")
