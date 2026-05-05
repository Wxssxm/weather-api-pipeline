"""Integration tests for the repository — requires real Postgres."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from weather_pipeline.api.models import CurrentWeather, ForecastResponse
from weather_pipeline.cities import DEFAULT_CITIES
from weather_pipeline.db.models import City, EtlRun
from weather_pipeline.db.repository import (
    finish_run,
    insert_observation,
    list_cities,
    start_run,
    upsert_cities,
)

pytestmark = pytest.mark.integration


def test_upsert_cities_is_idempotent(db_session: Session) -> None:
    first = upsert_cities(db_session, DEFAULT_CITIES)
    db_session.commit()
    second = upsert_cities(db_session, DEFAULT_CITIES)
    db_session.commit()

    assert first == len(DEFAULT_CITIES)
    assert second == 0
    assert len(list_cities(db_session)) == len(DEFAULT_CITIES)


def test_insert_observation_returns_row_then_no_op_on_conflict(db_session: Session) -> None:
    upsert_cities(db_session, DEFAULT_CITIES)
    db_session.commit()
    paris = db_session.scalar(select(City).where(City.name == "Paris"))
    assert paris is not None

    payload = ForecastResponse(
        latitude=paris.latitude,
        longitude=paris.longitude,
        timezone=paris.timezone,
        current=CurrentWeather(
            time=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
            interval=900,
            temperature_2m=20.0,
            relative_humidity_2m=70,
            apparent_temperature=19.5,
            precipitation=0.0,
            wind_speed_10m=10.0,
            wind_direction_10m=180,
            weather_code=2,
        ),
    )
    first = insert_observation(db_session, paris.id, payload)
    db_session.commit()
    second = insert_observation(db_session, paris.id, payload)
    db_session.commit()

    assert first is not None and first.temperature_c == 20.0
    assert second is None  # conflict -> no-op


def test_start_finish_run_records_status(db_session: Session) -> None:
    run = start_run(db_session)
    db_session.flush()
    finish_run(db_session, run, attempted=10, succeeded=10)
    db_session.commit()

    saved = db_session.get(EtlRun, run.id)
    assert saved is not None
    assert saved.status == "success"
    assert saved.cities_attempted == 10 and saved.cities_succeeded == 10
    assert saved.finished_at is not None


def test_finish_run_partial_status(db_session: Session) -> None:
    run = start_run(db_session)
    db_session.flush()
    finish_run(db_session, run, attempted=10, succeeded=7)
    db_session.commit()
    saved = db_session.get(EtlRun, run.id)
    assert saved is not None and saved.status == "partial"


def test_finish_run_failed_status(db_session: Session) -> None:
    run = start_run(db_session)
    db_session.flush()
    finish_run(db_session, run, attempted=10, succeeded=0, error="boom")
    db_session.commit()
    saved = db_session.get(EtlRun, run.id)
    assert saved is not None
    assert saved.status == "failed"
    assert saved.error_message == "boom"
