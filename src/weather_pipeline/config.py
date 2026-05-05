"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(default="weather")
    postgres_user: str = Field(default="weather")
    postgres_password: str = Field(default="weather_dev_only")

    open_meteo_base_url: str = Field(default="https://api.open-meteo.com/v1")
    http_timeout_seconds: int = Field(default=20, ge=1, le=120)
    http_max_retries: int = Field(default=4, ge=1, le=10)

    schedule_cron_hour: str = Field(default="*")
    schedule_cron_minute: str = Field(default="5")
    ingest_on_startup: bool = Field(default=True)

    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        configure_logging(_settings.log_level)
    return _settings


def reset_settings() -> None:
    """Test helper: drop the cached singleton so a fresh Settings() can be created."""
    global _settings
    _settings = None


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        ),
    )
