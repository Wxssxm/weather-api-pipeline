"""Pydantic models for Open-Meteo API responses.

Validation lives at the boundary: every payload that crosses the network is
parsed through these models before anything else touches it. If the API ever
adds, renames, or changes types of fields, the failure surfaces here with a
clear ValidationError instead of silently corrupting the warehouse.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CurrentWeather(BaseModel):
    """The `current` block returned by /v1/forecast?current=...

    Fields are aligned with the variables we request in `client.py`. The model
    is intentionally strict so that unexpected nulls fail fast.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    time: datetime
    interval: int
    temperature_2m: float = Field(alias="temperature_2m")
    relative_humidity_2m: int = Field(alias="relative_humidity_2m", ge=0, le=100)
    apparent_temperature: float = Field(alias="apparent_temperature")
    precipitation: float = Field(ge=0)
    wind_speed_10m: float = Field(alias="wind_speed_10m", ge=0)
    wind_direction_10m: int = Field(alias="wind_direction_10m", ge=0, le=360)
    weather_code: int = Field(alias="weather_code", ge=0)


class ForecastResponse(BaseModel):
    """Top-level shape of the /v1/forecast endpoint."""

    model_config = ConfigDict(extra="ignore")

    latitude: float
    longitude: float
    timezone: str
    elevation: float | None = None
    current: CurrentWeather
