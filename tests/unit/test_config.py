"""Tests for weather_pipeline.config."""

from __future__ import annotations

import pytest

from weather_pipeline.config import Settings


def test_defaults() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.postgres_host == "localhost"
    assert s.postgres_port == 5432
    assert s.http_timeout_seconds == 20
    assert s.http_max_retries == 4
    assert s.log_level == "INFO"


def test_database_url_format() -> None:
    s = Settings(  # type: ignore[call-arg]
        _env_file=None,
        postgres_host="db",
        postgres_port=5433,
        postgres_db="w",
        postgres_user="u",
        postgres_password="p",
    )
    assert s.database_url == "postgresql+psycopg://u:p@db:5433/w"


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_invalid_port_rejected(port: int) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, postgres_port=port)  # type: ignore[call-arg]


def test_log_level_uppercased() -> None:
    s = Settings(_env_file=None, log_level="debug")  # type: ignore[call-arg]
    assert s.log_level == "DEBUG"
