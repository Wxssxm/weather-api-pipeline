"""Tests for the Pydantic boundary models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from weather_pipeline.api.models import CurrentWeather, ForecastResponse


def test_forecast_response_parses_full_payload(sample_payload_dict: dict) -> None:
    fr = ForecastResponse.model_validate(sample_payload_dict)
    assert fr.latitude == sample_payload_dict["latitude"]
    assert fr.current.temperature_2m == 18.4
    assert fr.current.relative_humidity_2m == 63


def test_extra_fields_are_ignored(sample_payload_dict: dict) -> None:
    sample_payload_dict["unknown_field"] = "ok"
    sample_payload_dict["current"]["another"] = 999
    fr = ForecastResponse.model_validate(sample_payload_dict)
    assert fr.timezone == "Europe/Paris"


def test_humidity_out_of_range_rejected(sample_payload_dict: dict) -> None:
    sample_payload_dict["current"]["relative_humidity_2m"] = 150
    with pytest.raises(ValidationError):
        ForecastResponse.model_validate(sample_payload_dict)


def test_negative_precipitation_rejected(sample_payload_dict: dict) -> None:
    sample_payload_dict["current"]["precipitation"] = -1.0
    with pytest.raises(ValidationError):
        ForecastResponse.model_validate(sample_payload_dict)


def test_wind_direction_out_of_range_rejected(sample_payload_dict: dict) -> None:
    sample_payload_dict["current"]["wind_direction_10m"] = 999
    with pytest.raises(ValidationError):
        ForecastResponse.model_validate(sample_payload_dict)


def test_missing_required_field_rejected(sample_payload_dict: dict) -> None:
    del sample_payload_dict["current"]["wind_speed_10m"]
    with pytest.raises(ValidationError):
        ForecastResponse.model_validate(sample_payload_dict)


def test_current_weather_direct_construction() -> None:
    """Pydantic models can be built without populate_by_name aliases."""
    cw = CurrentWeather(
        time="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
        interval=900,
        temperature_2m=10.0,
        relative_humidity_2m=70,
        apparent_temperature=9.0,
        precipitation=0.0,
        wind_speed_10m=5.0,
        wind_direction_10m=90,
        weather_code=1,
    )
    assert cw.weather_code == 1
