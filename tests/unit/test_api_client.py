"""Tests for the OpenMeteoClient async client (respx-mocked)."""

from __future__ import annotations

import httpx
import pytest
import respx

from weather_pipeline.api.client import OpenMeteoClient
from weather_pipeline.api.models import ForecastResponse
from weather_pipeline.cities import DEFAULT_CITIES

BASE_URL = "https://api.open-meteo.com/v1"


@pytest.mark.asyncio
async def test_fetch_current_returns_validated_payload(sample_payload_dict: dict) -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/forecast").mock(
            return_value=httpx.Response(200, json=sample_payload_dict)
        )

        async with OpenMeteoClient(BASE_URL, timeout=5, max_retries=2) as client:
            result = await client.fetch_current(48.85, 2.35, "Europe/Paris")

        assert isinstance(result, ForecastResponse)
        assert result.current.temperature_2m == 18.4


@pytest.mark.asyncio
async def test_fetch_current_retries_on_5xx(sample_payload_dict: dict) -> None:
    with respx.mock:
        route = respx.get(f"{BASE_URL}/forecast").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json=sample_payload_dict),
            ]
        )

        async with OpenMeteoClient(BASE_URL, timeout=5, max_retries=3) as client:
            result = await client.fetch_current(48.85, 2.35)

        assert route.call_count == 2
        assert result.current.temperature_2m == 18.4


@pytest.mark.asyncio
async def test_fetch_current_4xx_does_not_retry() -> None:
    with respx.mock:
        route = respx.get(f"{BASE_URL}/forecast").mock(return_value=httpx.Response(400))

        async with OpenMeteoClient(BASE_URL, timeout=5, max_retries=3) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.fetch_current(0.0, 0.0)

        # 4xx exits via raise_for_status outside the retry catch list
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_fetch_for_cities_continues_past_failures(sample_payload_dict: dict) -> None:
    paris, london = DEFAULT_CITIES[0], DEFAULT_CITIES[1]
    with respx.mock:
        route = respx.get(f"{BASE_URL}/forecast")
        route.side_effect = [
            httpx.Response(200, json=sample_payload_dict),
            httpx.Response(400),
        ]

        async with OpenMeteoClient(BASE_URL, timeout=5, max_retries=2) as client:
            results = await client.fetch_for_cities([paris, london])

    assert paris.name in results and london.name not in results


@pytest.mark.asyncio
async def test_using_outside_context_manager_raises() -> None:
    client = OpenMeteoClient(BASE_URL)
    with pytest.raises(RuntimeError, match="async context manager"):
        await client.fetch_current(0.0, 0.0)
