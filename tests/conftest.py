"""Pytest fixtures shared across the test suite."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from weather_pipeline.api.models import CurrentWeather, ForecastResponse
from weather_pipeline.config import reset_settings
from weather_pipeline.db.session import get_session_factory, reset_engine


@pytest.fixture(autouse=True)
def _reset_global_state() -> Iterator[None]:
    """Make sure the per-test settings + engine cache do not leak between tests."""
    reset_settings()
    reset_engine()
    yield
    reset_settings()
    reset_engine()


@pytest.fixture
def sample_payload() -> ForecastResponse:
    """A minimal but realistic Open-Meteo /forecast response."""
    return ForecastResponse(
        latitude=48.85,
        longitude=2.35,
        timezone="Europe/Paris",
        elevation=42.0,
        current=CurrentWeather(
            time=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
            interval=900,
            temperature_2m=18.4,
            relative_humidity_2m=63,
            apparent_temperature=17.9,
            precipitation=0.0,
            wind_speed_10m=12.5,
            wind_direction_10m=240,
            weather_code=2,
        ),
    )


@pytest.fixture
def sample_payload_dict() -> dict:
    return {
        "latitude": 48.85,
        "longitude": 2.35,
        "timezone": "Europe/Paris",
        "elevation": 42.0,
        "current": {
            "time": "2026-05-06T12:00:00Z",
            "interval": 900,
            "temperature_2m": 18.4,
            "relative_humidity_2m": 63,
            "apparent_temperature": 17.9,
            "precipitation": 0.0,
            "wind_speed_10m": 12.5,
            "wind_direction_10m": 240,
            "weather_code": 2,
        },
    }


def _postgres_available() -> bool:
    """Heuristic: in CI we set POSTGRES_HOST=localhost and the service is up."""
    return os.environ.get("POSTGRES_HOST") is not None and os.environ.get("CI") is not None


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Real Postgres session for integration tests; truncates all tables on teardown.

    Skips automatically when no Postgres service is detected (CI sets POSTGRES_HOST + CI).
    """
    if not _postgres_available():
        pytest.skip("Postgres-dependent integration test (set POSTGRES_HOST + CI=1)")

    from alembic import command
    from alembic.config import Config as AlembicConfig

    # ensure schema is up-to-date once per test
    cfg = AlembicConfig("alembic.ini")
    command.upgrade(cfg, "head")

    Session = get_session_factory()
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.execute(
            text("TRUNCATE weather_observations, etl_runs, cities RESTART IDENTITY CASCADE")
        )
        session.commit()
        session.close()
