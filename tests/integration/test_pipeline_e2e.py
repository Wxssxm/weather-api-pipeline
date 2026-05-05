"""End-to-end pipeline tests against real Postgres with mocked HTTP."""

from __future__ import annotations

import httpx
import pytest
import respx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from weather_pipeline.cities import DEFAULT_CITIES
from weather_pipeline.db.models import EtlRun, WeatherObservation
from weather_pipeline.db.repository import upsert_cities

pytestmark = pytest.mark.integration

BASE_URL = "https://api.open-meteo.com/v1"


def test_full_pipeline_against_real_db(db_session: Session, sample_payload_dict: dict) -> None:
    upsert_cities(db_session, DEFAULT_CITIES)
    db_session.commit()
    db_session.close()

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{BASE_URL}/forecast").mock(
            return_value=httpx.Response(200, json=sample_payload_dict)
        )

        from weather_pipeline.pipeline import run_ingestion

        report = run_ingestion()

    assert report.attempted == 10
    assert report.succeeded == 10
    assert report.status == "success"

    # Verify the run + observations landed in Postgres
    from weather_pipeline.db.session import get_session_factory

    session = get_session_factory()()
    try:
        n_obs = session.scalar(select(func.count()).select_from(WeatherObservation))
        n_runs = session.scalar(select(func.count()).select_from(EtlRun))
        assert n_obs == 10
        assert n_runs >= 1
    finally:
        session.close()
