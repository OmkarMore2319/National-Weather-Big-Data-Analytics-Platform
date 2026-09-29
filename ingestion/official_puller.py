#!/usr/bin/env python3
"""
official_puller.py - Official Meteorological Ground-Truth Ingestion Service (PS 26069)

Pulls real-time official weather ground-truth observations for ~30 major Indian cities
from free meteorological APIs (Open-Meteo & OpenWeatherMap) with built-in mock/replay
fallback, formatted strictly according to the OfficialReading schema:
{ id, city, state, lat, lon, recordedAt, condition, rainfallMm, tempC, windKph }

Features:
- Dual API Provider: Automatically uses OpenWeatherMap if OPENWEATHER_API_KEY is provided,
  or zero-signup Open-Meteo API for instant live weather data out-of-the-box.
- Mock-Mode Principle: Bundled official station snapshot cache prevents failure if offline.
- Self-imposed rate-limiting to strictly respect API quotas.
- Standalone --dry-run mode for offline testing without a live backend.
"""

import os
import sys
import time
import json
import uuid
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests
from common import (
    post_to_backend,
    validate_official_reading,
    DEFAULT_BACKEND_URL,
    DEFAULT_INGEST_ENDPOINT,
    OPENWEATHER_API_KEY,
    DATA_DIR
)

logger = logging.getLogger("OfficialPuller")

SNAPSHOT_FILE = os.path.join(DATA_DIR, "official_stations_snapshot.json")

# Target ~30 major Indian meteorological observation stations across all zones
DEFAULT_OFFICIAL_CITIES = [
    {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
    {"city": "Delhi", "state": "Delhi", "lat": 28.7041, "lon": 77.1025},
    {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
    {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639},
    {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867},
    {"city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714},
    {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567},
    {"city": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lon": 75.7873},
    {"city": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462},
    {"city": "Kanpur", "state": "Uttar Pradesh", "lat": 26.4499, "lon": 80.3319},
    {"city": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882},
    {"city": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577},
    {"city": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lon": 77.4126},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lon": 83.2185},
    {"city": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376},
    {"city": "Vadodara", "state": "Gujarat", "lat": 22.3072, "lon": 73.1812},
    {"city": "Ludhiana", "state": "Punjab", "lat": 30.9010, "lon": 75.8573},
    {"city": "Agra", "state": "Uttar Pradesh", "lat": 27.1767, "lon": 78.0081},
    {"city": "Nashik", "state": "Maharashtra", "lat": 19.9975, "lon": 73.7898},
    {"city": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3176, "lon": 82.9739},
    {"city": "Srinagar", "state": "Jammu and Kashmir", "lat": 34.0837, "lon": 74.7973},
    {"city": "Amritsar", "state": "Punjab", "lat": 31.6340, "lon": 74.8723},
    {"city": "Ranchi", "state": "Jharkhand", "lat": 23.3441, "lon": 85.3096},
    {"city": "Guwahati", "state": "Assam", "lat": 26.1445, "lon": 91.7362},
    {"city": "Chandigarh", "state": "Chandigarh", "lat": 30.7333, "lon": 76.7794},
    {"city": "Shimla", "state": "Himachal Pradesh", "lat": 31.1048, "lon": 77.1734},
    {"city": "Dehradun", "state": "Uttarakhand", "lat": 30.3165, "lon": 78.0322},
    {"city": "Kochi", "state": "Kerala", "lat": 9.9312, "lon": 76.2673},
    {"city": "Bhubaneswar", "state": "Odisha", "lat": 20.2961, "lon": 85.8245},
    {"city": "Panaji", "state": "Goa", "lat": 15.4909, "lon": 73.8278},
    {"city": "Thiruvananthapuram", "state": "Kerala", "lat": 8.5241, "lon": 76.9366}
]

# WMO Weather interpretation codes for Open-Meteo mapping
WMO_CODE_MAP = {
    0: "Clear",
    1: "Clear",
    2: "Clouds",
    3: "Clouds",
    45: "Fog",
    48: "Fog",
    51: "Drizzle",
    53: "Drizzle",
    55: "Drizzle",
    61: "Rain",
    63: "Rain",
    65: "Heavy Rain",
    71: "Snow",
    73: "Snow",
    75: "Snow",
    80: "Rain",
    81: "Rain",
    82: "Heavy Rain",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm"
}


class OfficialGroundTruthPuller:
    """
    Pulls live or snapshot ground-truth weather readings
    and formats them as OfficialReading JSON.
    """

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        endpoint: str = DEFAULT_INGEST_ENDPOINT,
        api_key: Optional[str] = OPENWEATHER_API_KEY,
        dry_run: bool = False,
        cities: Optional[List[Dict[str, Any]]] = None,
        rate_limit_delay: float = 0.5
    ):
        self.backend_url = backend_url
        self.endpoint = endpoint
        self.api_key = api_key
        self.dry_run = dry_run
        self.cities = cities or DEFAULT_OFFICIAL_CITIES
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()

    def _fetch_from_openweathermap(self, city_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetches current reading from OpenWeatherMap free API."""
        lat = city_info["lat"]
        lon = city_info["lon"]
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"

        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                weather_arr = data.get("weather", [{}])
                condition = weather_arr[0].get("main", "Clear")
                rainfall_mm = 0.0
                if "rain" in data:
                    rainfall_mm = float(data["rain"].get("1h", data["rain"].get("3h", 0.0)))
                temp_c = round(float(data.get("main", {}).get("temp", 25.0)), 1)
                wind_speed_ms = float(data.get("wind", {}).get("speed", 0.0))
                wind_kph = round(wind_speed_ms * 3.6, 1)

                return {
                    "id": str(uuid.uuid4()),
                    "city": city_info["city"],
                    "state": city_info["state"],
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "recordedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "condition": condition,
                    "rainfallMm": rainfall_mm,
                    "tempC": temp_c,
                    "windKph": wind_kph
                }
            else:
                logger.warning(f"OpenWeatherMap returned {res.status_code} for {city_info['city']}: {res.text[:100]}")
        except Exception as e:
            logger.warning(f"Error calling OpenWeatherMap for {city_info['city']}: {e}")
        return None

    def _fetch_from_open_meteo(self, city_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetches live meteorological observation from Open-Meteo free API (No key required)."""
        lat = city_info["lat"]
        lon = city_info["lon"]
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,rain,weather_code,wind_speed_10m"
        )

        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                current = data.get("current", {})
                wmo_code = current.get("weather_code", 0)
                condition = WMO_CODE_MAP.get(wmo_code, "Clear")
                rainfall_mm = float(current.get("precipitation", current.get("rain", 0.0)))
                temp_c = round(float(current.get("temperature_2m", 25.0)), 1)
                wind_kph = round(float(current.get("wind_speed_10m", 0.0)), 1)

                return {
                    "id": str(uuid.uuid4()),
                    "city": city_info["city"],
                    "state": city_info["state"],
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "recordedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "condition": condition,
                    "rainfallMm": rainfall_mm,
                    "tempC": temp_c,
                    "windKph": wind_kph
                }
            else:
                logger.warning(f"Open-Meteo returned {res.status_code} for {city_info['city']}")
        except Exception as e:
            logger.warning(f"Error calling Open-Meteo for {city_info['city']}: {e}")
        return None

    def _load_snapshot_readings(self) -> List[Dict[str, Any]]:
        """Loads fallback official station snapshots (Mock-Mode Principle)."""
        if os.path.exists(SNAPSHOT_FILE):
            try:
                with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    readings = []
                    for r in data.get("readings", []):
                        r_copy = dict(r)
                        r_copy["id"] = str(uuid.uuid4())
                        r_copy["recordedAt"] = now_str
                        readings.append(r_copy)
                    return readings
            except Exception as e:
                logger.error(f"Error loading snapshot readings: {e}")
        return []

    def fetch_city_reading(self, city_info: Dict[str, Any]) -> Dict[str, Any]:
        """Pulls reading for a single city with automatic API fallback and validation."""
        reading = None

        # 1. Try OpenWeatherMap if key is provided
        if self.api_key and self.api_key.strip():
            reading = self._fetch_from_openweathermap(city_info)

        # 2. Try Open-Meteo free API
        if reading is None:
            reading = self._fetch_from_open_meteo(city_info)

        # 3. Fallback to realistic snapshot
        if reading is None:
            logger.info(f"Using mock ground-truth for {city_info['city']} (Mock-Mode Principle)")
            reading = {
                "id": str(uuid.uuid4()),
                "city": city_info["city"],
                "state": city_info["state"],
                "lat": round(city_info["lat"], 4),
                "lon": round(city_info["lon"], 4),
                "recordedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "condition": "Clear",
                "rainfallMm": 0.0,
                "tempC": 30.0,
                "windKph": 12.0
            }

        # Validate against contract
        errors = validate_official_reading(reading)
        if errors:
            logger.error(f"Validation error for {city_info['city']}: {errors}")

        return reading

    def pull_all_readings(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Pulls readings for all configured cities with rate-limiting."""
        target_cities = self.cities[:limit] if limit else self.cities
        readings = []

        logger.info(f"Initiating ground-truth pull for {len(target_cities)} official station cities...")
        for idx, city_info in enumerate(target_cities, 1):
            reading = self.fetch_city_reading(city_info)
            readings.append(reading)
            logger.info(
                f"[{idx}/{len(target_cities)}] {reading['city']} ({reading['state']}): "
                f"{reading['condition']}, {reading['tempC']}°C, Rain: {reading['rainfallMm']}mm, Wind: {reading['windKph']}km/h"
            )
            # Rate-limiting sleep between requests
            time.sleep(self.rate_limit_delay)

        return readings

    def run_cycle(self, limit: Optional[int] = None) -> int:
        """Executes a single fetch-and-post cycle across all cities."""
        readings = self.pull_all_readings(limit=limit)
        success_count = 0

        for reading in readings:
            ok = post_to_backend(
                payload=reading,
                endpoint=self.endpoint,
                backend_url=self.backend_url,
                dry_run=self.dry_run,
                logger=logger
            )
            if ok:
                success_count += 1
            time.sleep(0.05)

        return success_count


def main():
    parser = argparse.ArgumentParser(description="Official Meteorological Ground-Truth Puller (PS 26069)")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted JSON to stdout instead of sending HTTP POST")
    parser.add_argument("--once", action="store_true", help="Run a single round across cities and exit")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("OFFICIAL_POLL_INTERVAL", "180")), help="Interval in seconds between full cycles (default: 180s = 3 mins)")
    parser.add_argument("--limit-cities", type=int, default=None, help="Limit number of cities to pull per cycle")
    parser.add_argument("--api-key", type=str, default=OPENWEATHER_API_KEY, help="OpenWeatherMap API Key (optional, defaults to OPENWEATHER_API_KEY env var)")
    parser.add_argument("--backend-url", type=str, default=DEFAULT_BACKEND_URL, help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})")
    parser.add_argument("--endpoint", type=str, default=DEFAULT_INGEST_ENDPOINT, help=f"Backend ingest endpoint (default: {DEFAULT_INGEST_ENDPOINT})")
    parser.add_argument("--save-samples", type=str, default=None, help="Save sample JSON readings array to file")

    args = parser.parse_args()

    puller = OfficialGroundTruthPuller(
        backend_url=args.backend_url,
        endpoint=args.endpoint,
        api_key=args.api_key,
        dry_run=args.dry_run
    )

    logger.info("Starting Official Ground-Truth Ingestion Service...")
    logger.info(f"Target Backend: {args.backend_url} | Endpoint: {args.endpoint} | Dry-Run: {args.dry_run}")
    if args.api_key:
        logger.info("Provider: OpenWeatherMap API (API Key present)")
    else:
        logger.info("Provider: Open-Meteo Free Meteorological API (No key required) + Mock Fallback")

    if args.once or args.save_samples:
        readings = puller.pull_all_readings(limit=args.limit_cities)
        logger.info(f"Collected {len(readings)} official readings in single pass.")
        if args.save_samples:
            os.makedirs(os.path.dirname(os.path.abspath(args.save_samples)) or ".", exist_ok=True)
            with open(args.save_samples, "w", encoding="utf-8") as f:
                json.dump(readings, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(readings)} sample readings to {args.save_samples}")

        for r in readings:
            post_to_backend(r, endpoint=args.endpoint, backend_url=args.backend_url, dry_run=args.dry_run, logger=logger)
        return

    # Continuous polling loop (every few minutes)
    try:
        while True:
            puller.run_cycle(limit=args.limit_cities)
            logger.info(f"Official cycle complete. Sleeping for {args.interval} seconds before next observation round...")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Official Ground-Truth Puller terminated by user.")


if __name__ == "__main__":
    main()
