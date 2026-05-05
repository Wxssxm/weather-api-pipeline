"""Initial schema: cities, weather_observations, etl_runs.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", "country_code", name="uq_cities_name_country"),
    )

    op.create_table(
        "weather_observations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("apparent_temperature_c", sa.Float(), nullable=False),
        sa.Column("relative_humidity_pct", sa.Integer(), nullable=False),
        sa.Column("precipitation_mm", sa.Float(), nullable=False),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=False),
        sa.Column("wind_direction_deg", sa.Integer(), nullable=False),
        sa.Column("weather_code", sa.Integer(), nullable=False),
        sa.UniqueConstraint("city_id", "observed_at", name="uq_obs_city_observed"),
    )
    op.create_index("ix_obs_observed_at", "weather_observations", ["observed_at"])

    op.create_table(
        "etl_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("cities_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cities_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(2000), nullable=True),
    )
    op.create_index("ix_runs_started_at", "etl_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_started_at", table_name="etl_runs")
    op.drop_table("etl_runs")
    op.drop_index("ix_obs_observed_at", table_name="weather_observations")
    op.drop_table("weather_observations")
    op.drop_table("cities")
