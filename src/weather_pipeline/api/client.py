"""Async HTTP client for Open-Meteo with retry, timeout, and validation.

Open-Meteo is free and key-less but still rate-limited. The retry strategy
uses exponential backoff on transient errors (5xx + connection issues) and
gives up immediately on 4xx (we don't want to spam invalid requests).
"""

from __future__ import annotations

from collections.abc import Iterable

import httpx
from loguru import logger
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from weather_pipeline.api.models import ForecastResponse
from weather_pipeline.cities import City

CURRENT_VARIABLES: tuple[str, ...] = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "weather_code",
)


class TransientUpstreamError(Exception):
    """Raised on 5xx responses so tenacity can retry; 4xx escapes via HTTPStatusError."""


class OpenMeteoClient:
    """Thin async wrapper around the /v1/forecast endpoint."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 20,
        max_retries: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> OpenMeteoClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_current(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "auto",
        variables: Iterable[str] = CURRENT_VARIABLES,
    ) -> ForecastResponse:
        """Fetch the current weather snapshot for one (lat, lon)."""
        if self._client is None:
            raise RuntimeError("Use OpenMeteoClient as an async context manager.")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(variables),
            "timezone": timezone,
        }

        retrying = AsyncRetrying(
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, TransientUpstreamError)
            ),
            wait=wait_exponential(multiplier=2, min=2, max=20),
            stop=stop_after_attempt(self._max_retries),
            reraise=True,
        )

        async for attempt in retrying:
            with attempt:
                resp = await self._client.get(f"{self._base_url}/forecast", params=params)
                if resp.status_code >= 500:
                    raise TransientUpstreamError(f"upstream {resp.status_code}")
                resp.raise_for_status()  # 4xx -> HTTPStatusError, not retried
                payload = resp.json()
                return ForecastResponse.model_validate(payload)

        raise RuntimeError("Unreachable: AsyncRetrying always returns or raises.")

    async def fetch_for_cities(self, cities: Iterable[City]) -> dict[str, ForecastResponse]:
        """Fetch sequentially, keyed by city name. Failures don't abort siblings."""
        results: dict[str, ForecastResponse] = {}
        for city in cities:
            try:
                results[city.name] = await self.fetch_current(
                    city.latitude, city.longitude, city.timezone
                )
            except (httpx.HTTPError, ValueError) as exc:
                logger.error("fetch failed for {}: {}", city.name, exc)
        return results
