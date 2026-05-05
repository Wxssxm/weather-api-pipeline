"""Pipeline orchestration tests with mocked DB and API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weather_pipeline.api.models import ForecastResponse
from weather_pipeline.db.models import City, EtlRun


@pytest.fixture
def fake_session_scope():
    """Patch session_scope so the pipeline doesn't touch a real DB."""
    fake_session = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake_session
    cm.__exit__.return_value = None
    with patch("weather_pipeline.pipeline.session_scope", return_value=cm) as patched:
        yield patched, fake_session


def _fake_run(run_id: int = 42) -> EtlRun:
    run = EtlRun(id=run_id)
    run.cities_attempted = 0
    run.cities_succeeded = 0
    run.status = "running"
    return run


def _fake_city(id_: int, name: str) -> City:
    c = City(
        id=id_,
        name=name,
        country_code="XX",
        latitude=0.0,
        longitude=0.0,
        timezone="UTC",
    )
    return c


def test_run_ingestion_no_cities_finishes_success(fake_session_scope) -> None:
    _, session = fake_session_scope
    run = _fake_run()
    session.get.return_value = run
    with (
        patch("weather_pipeline.pipeline.start_run", return_value=run),
        patch("weather_pipeline.pipeline.list_cities", return_value=[]),
        patch("weather_pipeline.pipeline.finish_run") as fr,
    ):
        from weather_pipeline.pipeline import run_ingestion

        report = run_ingestion()

    assert report.attempted == 0 and report.succeeded == 0
    fr.assert_called_once()


def test_run_ingestion_happy_path(fake_session_scope, sample_payload: ForecastResponse) -> None:
    _, session = fake_session_scope
    run = _fake_run()
    session.get.return_value = run
    cities = [_fake_city(1, "Paris"), _fake_city(2, "London")]

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = None
    fake_client.fetch_current = AsyncMock(return_value=sample_payload)

    with (
        patch("weather_pipeline.pipeline.start_run", return_value=run),
        patch("weather_pipeline.pipeline.list_cities", return_value=cities),
        patch("weather_pipeline.pipeline.OpenMeteoClient", return_value=fake_client),
        patch("weather_pipeline.pipeline.insert_observation", return_value=MagicMock()),
        patch("weather_pipeline.pipeline.finish_run") as finish,
    ):
        from weather_pipeline.pipeline import run_ingestion

        report = run_ingestion()

    assert report.attempted == 2
    assert report.succeeded == 2
    assert report.inserted == 2
    finish.assert_called_once()
    _, kwargs = finish.call_args
    assert kwargs["attempted"] == 2 and kwargs["succeeded"] == 2 and kwargs.get("error") is None


def test_run_ingestion_per_city_failure_continues(
    fake_session_scope, sample_payload: ForecastResponse
) -> None:
    _, session = fake_session_scope
    run = _fake_run()
    session.get.return_value = run
    cities = [_fake_city(1, "A"), _fake_city(2, "B")]

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = None
    fake_client.fetch_current = AsyncMock(side_effect=[sample_payload, RuntimeError("boom")])

    with (
        patch("weather_pipeline.pipeline.start_run", return_value=run),
        patch("weather_pipeline.pipeline.list_cities", return_value=cities),
        patch("weather_pipeline.pipeline.OpenMeteoClient", return_value=fake_client),
        patch("weather_pipeline.pipeline.insert_observation", return_value=MagicMock()),
        patch("weather_pipeline.pipeline.finish_run"),
    ):
        from weather_pipeline.pipeline import run_ingestion

        report = run_ingestion()

    assert report.attempted == 2 and report.succeeded == 1
