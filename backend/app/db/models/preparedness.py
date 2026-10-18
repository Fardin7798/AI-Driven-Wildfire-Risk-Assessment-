from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PreparednessItem(Base):
    __tablename__ = "preparedness_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hazard: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'wildfire' | 'air_quality'
    stage: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'before' | 'during' | 'after'
    audience: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(255), nullable=False)
    lang: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
