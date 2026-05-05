"""Typer CLI for the weather pipeline."""

from __future__ import annotations

from pathlib import Path

import typer
from alembic import command
from alembic.config import Config as AlembicConfig
from loguru import logger
from rich.console import Console
from rich.table import Table

from weather_pipeline.cities import DEFAULT_CITIES
from weather_pipeline.db.repository import list_cities, upsert_cities
from weather_pipeline.db.session import session_scope
from weather_pipeline.pipeline import run_ingestion
from weather_pipeline.scheduler.worker import run_scheduler

PROJECT_ROOT = Path(__file__).resolve().parents[2]

app = typer.Typer(
    name="weather",
    help="Scheduled multi-city weather ingestion (Open-Meteo -> PostgreSQL).",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _alembic_config() -> AlembicConfig:
    return AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))


@app.command()
def migrate() -> None:
    """Apply Alembic migrations to the configured database."""
    command.upgrade(_alembic_config(), "head")


@app.command(name="seed-cities")
def seed_cities() -> None:
    """Insert the 10 default cities (idempotent on conflict)."""
    with session_scope() as session:
        inserted = upsert_cities(session, DEFAULT_CITIES)
    logger.info("Seeded cities: {} new rows inserted", inserted)


@app.command(name="list-cities")
def list_cities_cmd() -> None:
    """Print the current city seed table."""
    with session_scope() as session:
        cities = list_cities(session)

    table = Table(title=f"{len(cities)} cities")
    for col in ("id", "name", "country", "lat", "lon", "tz"):
        table.add_column(col)
    for c in cities:
        table.add_row(
            str(c.id), c.name, c.country_code, f"{c.latitude:.4f}", f"{c.longitude:.4f}", c.timezone
        )
    console.print(table)


@app.command(name="ingest-once")
def ingest_once() -> None:
    """Run a single ingestion pass across all seeded cities."""
    report = run_ingestion()
    console.print(report)


@app.command(name="run-scheduler")
def run_scheduler_cmd() -> None:
    """Start the long-lived scheduler (blocking)."""
    run_scheduler()


if __name__ == "__main__":
    app()
