"""CRUD helpers around the ORM models — keeps query logic out of the pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from weather_pipeline.api.models import ForecastResponse
from weather_pipeline.cities import City as CityDataclass
from weather_pipeline.db.models import City, EtlRun, WeatherObservation


def upsert_cities(session: Session, cities: Iterable[CityDataclass]) -> int:
    """Idempotently insert the seed cities. Returns the number of rows inserted."""
    rows = [
        {
            "name": c.name,
            "country_code": c.country_code,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "timezone": c.timezone,
        }
        for c in cities
    ]
    if not rows:
        return 0
    stmt = (
        pg_insert(City)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["name", "country_code"])
        .returning(City.id)
    )
    return len(session.execute(stmt).all())


def list_cities(session: Session) -> list[City]:
    return list(session.scalars(select(City).order_by(City.name)))


def insert_observation(
    session: Session, city_id: int, payload: ForecastResponse
) -> WeatherObservation | None:
    """Insert one observation; on (city_id, observed_at) conflict, return None."""
    cur = payload.current
    stmt = (
        pg_insert(WeatherObservation)
        .values(
            city_id=city_id,
            observed_at=cur.time,
            temperature_c=cur.temperature_2m,
            apparent_temperature_c=cur.apparent_temperature,
            relative_humidity_pct=cur.relative_humidity_2m,
            precipitation_mm=cur.precipitation,
            wind_speed_kmh=cur.wind_speed_10m,
            wind_direction_deg=cur.wind_direction_10m,
            weather_code=cur.weather_code,
        )
        .on_conflict_do_nothing(index_elements=["city_id", "observed_at"])
        .returning(WeatherObservation.id)
    )
    new_id = session.execute(stmt).scalar_one_or_none()
    if new_id is None:
        return None
    return session.get(WeatherObservation, new_id)


def start_run(session: Session) -> EtlRun:
    run = EtlRun(status="running")
    session.add(run)
    session.flush()
    return run


def finish_run(
    session: Session,
    run: EtlRun,
    *,
    attempted: int,
    succeeded: int,
    error: str | None = None,
) -> None:
    run.cities_attempted = attempted
    run.cities_succeeded = succeeded
    run.finished_at = datetime.now(tz=UTC)
    if error is not None:
        run.status = "failed"
        run.error_message = error[:2000]
    elif succeeded == 0 and attempted > 0:
        run.status = "failed"
        run.error_message = "All cities failed."
    elif succeeded < attempted:
        run.status = "partial"
    else:
        run.status = "success"
    session.add(run)
