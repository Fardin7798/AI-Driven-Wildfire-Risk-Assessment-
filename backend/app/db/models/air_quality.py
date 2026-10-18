from datetime import date, datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AQStation(Base):
    __tablename__ = "aq_stations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="cpcb")
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    geom: Mapped[Any | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True), nullable=True
    )

    region_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    observations = relationship(
        "AQObservation", back_populates="station", cascade="all, delete-orphan"
    )


class AQObservation(Base):
    __tablename__ = "aq_observations"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "station_id",
            "region_id",
            "observed_at_utc",
            name="uq_aq_obs_provider_station_region_time",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    station_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aq_stations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    region_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("regions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    observed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    o3: Mapped[float | None] = mapped_column(Float, nullable=True)
    nh3: Mapped[float | None] = mapped_column(Float, nullable=True)

    aqi: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    aqi_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="open_meteo")

    station = relationship("AQStation", back_populates="observations")
    region = relationship("Region", back_populates="aq_observations")


class AQForecast(Base):
    __tablename__ = "aq_forecasts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)

    pm25_pred: Mapped[float | None] = mapped_column(Float, nullable=True)
    aqi_pred: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aqi_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    region = relationship("Region", back_populates="aq_forecasts")
