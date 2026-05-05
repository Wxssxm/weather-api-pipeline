"""Tests for weather_pipeline.cities seed list."""

from __future__ import annotations

from weather_pipeline.cities import DEFAULT_CITIES


def test_ten_cities() -> None:
    assert len(DEFAULT_CITIES) == 10


def test_unique_per_name_and_country() -> None:
    keys = {(c.name, c.country_code) for c in DEFAULT_CITIES}
    assert len(keys) == len(DEFAULT_CITIES)


def test_lat_lon_in_range() -> None:
    for c in DEFAULT_CITIES:
        assert -90.0 <= c.latitude <= 90.0, c
        assert -180.0 <= c.longitude <= 180.0, c


def test_country_codes_two_chars() -> None:
    for c in DEFAULT_CITIES:
        assert len(c.country_code) == 2
        assert c.country_code.isupper()


def test_geographic_spread() -> None:
    """Coverage: at least one city in each hemisphere."""
    lats = [c.latitude for c in DEFAULT_CITIES]
    lons = [c.longitude for c in DEFAULT_CITIES]
    assert any(la > 0 for la in lats) and any(la < 0 for la in lats)
    assert any(lo > 0 for lo in lons) and any(lo < 0 for lo in lons)
