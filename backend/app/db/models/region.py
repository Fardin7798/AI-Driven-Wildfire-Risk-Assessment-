from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True, default="IN")
    admin_level: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    gadm_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    geom: Mapped[Any | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=True), nullable=True
    )
    centroid: Mapped[Any | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True), nullable=True
    )

    area_km2: Mapped[float | None] = mapped_column(Float, nullable=True)
    landcover: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")

    fire_detections = relationship(
        "FireDetection", back_populates="region", cascade="all, delete-orphan"
    )
    weather_records = relationship(
        "WeatherDaily", back_populates="region", cascade="all, delete-orphan"
    )
    fwi_records = relationship("FWIState", back_populates="region", cascade="all, delete-orphan")
    risk_predictions = relationship(
        "RiskPrediction", back_populates="region", cascade="all, delete-orphan"
    )
    aq_observations = relationship(
        "AQObservation", back_populates="region", cascade="all, delete-orphan"
    )
    aq_forecasts = relationship("AQForecast", back_populates="region", cascade="all, delete-orphan")

    @property
    def centroid_lat(self) -> float | None:
        if self.centroid is None:
            return None
        try:
            from geoalchemy2.shape import to_shape

            pt = to_shape(self.centroid)
            return float(pt.y)
        except Exception:
            return None

    @property
    def centroid_lon(self) -> float | None:
        if self.centroid is None:
            return None
        try:
            from geoalchemy2.shape import to_shape

            pt = to_shape(self.centroid)
            return float(pt.x)
        except Exception:
            return None
