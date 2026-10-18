from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.db.base import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True, default="IN")
    admin_level: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    gadm_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    geom: Mapped[Optional[Any]] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=True), nullable=True)
    centroid: Mapped[Optional[Any]] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True), nullable=True)

    area_km2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    landcover: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")

    fire_detections = relationship("FireDetection", back_populates="region", cascade="all, delete-orphan")
    weather_records = relationship("WeatherDaily", back_populates="region", cascade="all, delete-orphan")
    fwi_records = relationship("FWIState", back_populates="region", cascade="all, delete-orphan")
    risk_predictions = relationship("RiskPrediction", back_populates="region", cascade="all, delete-orphan")
    aq_observations = relationship("AQObservation", back_populates="region", cascade="all, delete-orphan")
    aq_forecasts = relationship("AQForecast", back_populates="region", cascade="all, delete-orphan")
