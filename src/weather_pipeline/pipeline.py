"""End-to-end ingestion: fetch all cities, persist observations, audit the run."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from loguru import logger

from weather_pipeline.api.client import OpenMeteoClient
from weather_pipeline.config import Settings, get_settings
from weather_pipeline.db.repository import (
    finish_run,
    insert_observation,
    list_cities,
    start_run,
)
from weather_pipeline.db.session import session_scope


@dataclass(frozen=True, slots=True)
class IngestionReport:
    run_id: int
    attempted: int
    succeeded: int
    inserted: int  # rows actually inserted (excludes upsert no-ops)
    status: str


async def _ingest(settings: Settings) -> IngestionReport:
    with session_scope() as session:
        run = start_run(session)
        cities = list_cities(session)
        run_id = run.id

    if not cities:
        logger.warning("No cities seeded; run `weather seed-cities` first.")
        with session_scope() as session:
            run = session.get(type(run), run_id)
            assert run is not None
            finish_run(session, run, attempted=0, succeeded=0)
        return IngestionReport(
            run_id=run_id, attempted=0, succeeded=0, inserted=0, status="success"
        )

    succeeded = 0
    inserted = 0
    error: str | None = None

    try:
        async with OpenMeteoClient(
            base_url=settings.open_meteo_base_url,
            timeout=settings.http_timeout_seconds,
            max_retries=settings.http_max_retries,
        ) as client:
            for city in cities:
                try:
                    payload = await client.fetch_current(
                        city.latitude, city.longitude, city.timezone
                    )
                except Exception as exc:
                    logger.error("API call failed for {}: {}", city.name, exc)
                    continue

                with session_scope() as session:
                    obs = insert_observation(session, city.id, payload)

                succeeded += 1
                if obs is not None:
                    inserted += 1

    except Exception as exc:
        error = str(exc)
        logger.exception("Pipeline run aborted")

    with session_scope() as session:
        run = session.get(type(run), run_id)
        assert run is not None
        finish_run(session, run, attempted=len(cities), succeeded=succeeded, error=error)
        status = run.status

    logger.info(
        "Run {id}: attempted={a} succeeded={s} inserted={i} status={st}",
        id=run_id,
        a=len(cities),
        s=succeeded,
        i=inserted,
        st=status,
    )
    return IngestionReport(
        run_id=run_id, attempted=len(cities), succeeded=succeeded, inserted=inserted, status=status
    )


def run_ingestion() -> IngestionReport:
    """Sync entry point used by the scheduler and CLI."""
    settings = get_settings()
    return asyncio.run(_ingest(settings))
