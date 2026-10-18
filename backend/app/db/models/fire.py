from datetime import datetime
from typing import Any, Optional
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.db.base import Base


class FireDetection(Base):
    __tablename__ = "fire_detections"
    __table_args__ = (
        UniqueConstraint("source", "acq_datetime_utc", "lat", "lon", name="uq_fire_detections_source_time_lat_lon"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    satellite: Mapped[str] = mapped_column(String(20), nullable=False)
    instrument: Mapped[str] = mapped_column(String(20), nullable=False)
    acq_datetime_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[Optional[Any]] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True), nullable=True)
    brightness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    frp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    daynight: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    landcover_class: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    region_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True, index=True)
    region = relationship("Region", back_populates="fire_detections")
