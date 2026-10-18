from datetime import date
from typing import Optional
from sqlalchemy import BigInteger, Boolean, Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    region_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("regions.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    is_forecast: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=False)

    temp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rh_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rh_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precip_sum: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    et0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_moisture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="open_meteo")

    region = relationship("Region", back_populates="weather_records")


class FWIState(Base):
    __tablename__ = "fwi_state"

    region_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("regions.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    ffmc: Mapped[float] = mapped_column(Float, nullable=False)
    dmc: Mapped[float] = mapped_column(Float, nullable=False)
    dc: Mapped[float] = mapped_column(Float, nullable=False)
    isi: Mapped[float] = mapped_column(Float, nullable=False)
    bui: Mapped[float] = mapped_column(Float, nullable=False)
    fwi: Mapped[float] = mapped_column(Float, nullable=False)

    region = relationship("Region", back_populates="fwi_records")
