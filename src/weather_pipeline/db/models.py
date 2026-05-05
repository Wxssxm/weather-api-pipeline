"""SQLAlchemy ORM models — also the source of truth for Alembic autogeneration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    observations: Mapped[list[WeatherObservation]] = relationship(
        back_populates="city", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name", "country_code", name="uq_cities_name_country"),)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    apparent_temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    relative_humidity_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    precipitation_mm: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    wind_direction_deg: Mapped[int] = mapped_column(Integer, nullable=False)
    weather_code: Mapped[int] = mapped_column(Integer, nullable=False)

    city: Mapped[City] = relationship(back_populates="observations")

    __table_args__ = (
        UniqueConstraint("city_id", "observed_at", name="uq_obs_city_observed"),
        Index("ix_obs_observed_at", "observed_at"),
    )


class EtlRun(Base):
    """Audit log: one row per scheduled (or one-shot) ingestion attempt."""

    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    cities_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cities_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    __table_args__ = (Index("ix_runs_started_at", "started_at"),)
