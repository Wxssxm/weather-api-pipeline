"""Default cities seeded into the `cities` table on first run.

The selection covers a wide geographic spread (latitude, longitude, hemisphere)
so dashboards show contrast — e.g. winter Sydney vs summer Paris, or a humid
Singapore next to a dry Dubai.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class City:
    name: str
    country_code: str
    latitude: float
    longitude: float
    timezone: str


DEFAULT_CITIES: tuple[City, ...] = (
    City("Paris", "FR", 48.8566, 2.3522, "Europe/Paris"),
    City("London", "GB", 51.5074, -0.1278, "Europe/London"),
    City("New York", "US", 40.7128, -74.0060, "America/New_York"),
    City("Tokyo", "JP", 35.6762, 139.6503, "Asia/Tokyo"),
    City("Sao Paulo", "BR", -23.5505, -46.6333, "America/Sao_Paulo"),
    City("Cape Town", "ZA", -33.9249, 18.4241, "Africa/Johannesburg"),
    City("Sydney", "AU", -33.8688, 151.2093, "Australia/Sydney"),
    City("Mumbai", "IN", 19.0760, 72.8777, "Asia/Kolkata"),
    City("Singapore", "SG", 1.3521, 103.8198, "Asia/Singapore"),
    City("Dubai", "AE", 25.2048, 55.2708, "Asia/Dubai"),
)
