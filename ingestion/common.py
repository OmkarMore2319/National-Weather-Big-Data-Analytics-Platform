"""
common.py - Shared utilities for PS 26069 Weather Data Ingestion Service

Provides:
- Configuration management from environment variables
- City & state lookup against the static Indian cities dataset (~300 cities)
- Robust HTTP POST client with exponential backoff & dry-run support
- Contract schema validation
- Formatted console logging
"""

import os
import re
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry
except ImportError:
    requests = None

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8010")
DEFAULT_INGEST_ENDPOINT = os.environ.get("INGEST_ENDPOINT", "/api/v1/ingest/internal")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", None)
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "7180cb6d3a1e86051e71e9abfdc4c779")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CITIES_FILE = os.path.join(DATA_DIR, "indian_cities.json")


# ---------------------------------------------------------------------------
# City & Geo Lookup Table
# ---------------------------------------------------------------------------
class CityGeoLookup:
    """
    Local fast lookup table for ~300 Indian cities and all states/UTs.
    Avoids any external paid geocoding API per-request.
    """
    _instance = None

    def __init__(self, cities_path: str = CITIES_FILE):
        self.cities = []
        self.state_centers = {}
        self.city_lookup_map = {}  # normalized name/alias -> city dict
        self._compiled_patterns = []

        if os.path.exists(cities_path):
            with open(cities_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cities = data.get("cities", [])
                self.state_centers = data.get("stateCenters", {})
        else:
            logging.warning(f"Cities database not found at {cities_path}, using fallback.")
            self._init_fallback()

        self._build_indexes()

    def _init_fallback(self):
        self.cities = [
            {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777, "aliases": ["Bombay"]},
            {"city": "Delhi", "state": "Delhi", "lat": 28.7041, "lon": 77.1025, "aliases": ["New Delhi"]},
            {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946, "aliases": ["Bangalore"]},
            {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707, "aliases": ["Madras"]},
            {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639, "aliases": ["Calcutta"]},
            {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867, "aliases": []}
        ]
        self.state_centers = {
            "Maharashtra": {"lat": 19.7515, "lon": 75.7139, "capital": "Mumbai"},
            "Delhi": {"lat": 28.7041, "lon": 77.1025, "capital": "Delhi"},
            "Karnataka": {"lat": 15.3173, "lon": 75.7139, "capital": "Bengaluru"},
            "Tamil Nadu": {"lat": 11.1271, "lon": 78.6569, "capital": "Chennai"},
            "West Bengal": {"lat": 22.9868, "lon": 87.8550, "capital": "Kolkata"},
            "Telangana": {"lat": 18.1124, "lon": 79.0193, "capital": "Hyderabad"}
        }

    def _build_indexes(self):
        # Index all city names and aliases (sorted by length descending for greedy matching)
        all_terms = []
        for city_info in self.cities:
            c_name = city_info["city"]
            self.city_lookup_map[c_name.lower()] = city_info
            all_terms.append((c_name, city_info))

            for alias in city_info.get("aliases", []):
                self.city_lookup_map[alias.lower()] = city_info
                all_terms.append((alias, city_info))

        # Also index state names
        for state_name, center_info in self.state_centers.items():
            state_entry = {
                "city": center_info.get("capital", state_name),
                "state": state_name,
                "lat": center_info["lat"],
                "lon": center_info["lon"],
                "aliases": []
            }
            self.city_lookup_map[state_name.lower()] = state_entry
            all_terms.append((state_name, state_entry))

        # Sort longer phrases first so "New Delhi" matches before "Delhi"
        all_terms.sort(key=lambda x: len(x[0]), reverse=True)

        # Build regex patterns
        self._compiled_patterns = [
            (re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE), entry)
            for term, entry in all_terms
        ]

    @classmethod
    def get_instance(cls) -> 'CityGeoLookup':
        if cls._instance is None:
            cls._instance = CityGeoLookup()
        return cls._instance

    def match_location(self, text: str) -> Tuple[Optional[str], Optional[str], float, float]:
        """
        Scans text for mentions of Indian cities or states.
        Returns: (city, state, lat, lon)
        Defaults to National Center coordinates if no specific location is found.
        """
        if not text:
            return (None, None, 20.5937, 78.9629)

        for pattern, city_entry in self._compiled_patterns:
            if pattern.search(text):
                return (
                    city_entry.get("city"),
                    city_entry.get("state"),
                    city_entry.get("lat"),
                    city_entry.get("lon")
                )

        # Default fallback: India geographic center coordinates
        return (None, None, 20.5937, 78.9629)

    def get_city_coords(self, city_name: str) -> Optional[Dict[str, Any]]:
        """Exact lookup by city name."""
        return self.city_lookup_map.get(city_name.lower().strip())


# ---------------------------------------------------------------------------
# Shared Technical Contract Validation
# ---------------------------------------------------------------------------
VALID_SOURCES = {"CITIZEN", "SOCIAL_SIMULATED", "SOCIAL_REAL", "NEWS_RSS", "OFFICIAL_STATION"}
VALID_EVENT_TYPES = {
    "RAINFALL", "THUNDERSTORM", "FLOODING", "HEATWAVE",
    "FOG", "DUST_STORM", "STRONG_WIND", "UNKNOWN"
}
VALID_VERIFICATION_STATUSES = {"PENDING", "VERIFIED", "SUSPICIOUS", "REJECTED", "DUPLICATE"}


def validate_raw_report(payload: Dict[str, Any]) -> List[str]:
    """
    Validates a RawReport payload destined for POST /api/v1/ingest/internal.
    Returns list of error messages (empty if valid).
    """
    errors = []
    if not isinstance(payload, dict):
        return ["Payload must be a dictionary"]

    # source
    source = payload.get("source")
    if not source or source not in VALID_SOURCES:
        errors.append(f"Invalid or missing 'source': {source}. Must be one of {VALID_SOURCES}")

    # rawText
    raw_text = payload.get("rawText")
    if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
        errors.append("Field 'rawText' must be a non-empty string")

    # mediaUrls
    media_urls = payload.get("mediaUrls")
    if media_urls is not None and not isinstance(media_urls, list):
        errors.append("Field 'mediaUrls' must be a list of strings")

    # reportedAt
    reported_at = payload.get("reportedAt")
    if not reported_at or not isinstance(reported_at, str):
        errors.append("Field 'reportedAt' must be an ISO 8601 string")

    # lat and lon
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
        errors.append(f"Invalid 'lat': {lat}")
    if lon is None or not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
        errors.append(f"Invalid 'lon': {lon}")

    # sourceMeta
    source_meta = payload.get("sourceMeta")
    if source_meta is not None and not isinstance(source_meta, dict):
        errors.append("Field 'sourceMeta' must be a dictionary")

    return errors


def validate_official_reading(payload: Dict[str, Any]) -> List[str]:
    """
    Validates an OfficialReading payload matching the contract:
    { id, city, state, lat, lon, recordedAt, condition, rainfallMm, tempC, windKph }
    """
    errors = []
    if not isinstance(payload, dict):
        return ["Payload must be a dictionary"]

    required_fields = ["id", "city", "state", "lat", "lon", "recordedAt", "condition", "rainfallMm", "tempC", "windKph"]
    for f in required_fields:
        if f not in payload or payload[f] is None:
            errors.append(f"Missing required field '{f}'")

    if "lat" in payload and not (-90 <= payload["lat"] <= 90):
        errors.append(f"Invalid 'lat': {payload.get('lat')}")
    if "lon" in payload and not (-180 <= payload["lon"] <= 180):
        errors.append(f"Invalid 'lon': {payload.get('lon')}")
    if "recordedAt" in payload and not isinstance(payload["recordedAt"], str):
        errors.append("Field 'recordedAt' must be an ISO string")

    return errors


# ---------------------------------------------------------------------------
# HTTP Client with Retry & Exponential Backoff
# ---------------------------------------------------------------------------
def create_retry_session(retries: int = 3, backoff_factor: float = 0.5) -> Optional[Any]:
    if requests is None:
        return None
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_shared_session = None


def get_http_session():
    global _shared_session
    if _shared_session is None:
        _shared_session = create_retry_session(retries=3, backoff_factor=0.5)
    return _shared_session


def post_to_backend(
    payload: Dict[str, Any],
    endpoint: str = DEFAULT_INGEST_ENDPOINT,
    backend_url: str = DEFAULT_BACKEND_URL,
    dry_run: bool = False,
    logger: Optional[logging.Logger] = None,
    timeout: float = 20.0
) -> bool:
    """
    POSTs a JSON payload to the backend service.
    In --dry-run mode: prints formatted JSON payload to stdout and returns True.
    In live mode: executes HTTP POST with retry + backoff; gracefully handles connection errors without crashing.
    """
    log = logger or logging.getLogger("IngestionPoster")
    full_url = f"{backend_url.rstrip('/')}/{endpoint.lstrip('/')}"

    if dry_run:
        print("\n" + "=" * 70)
        print(f"[DRY-RUN] Would POST to: {full_url}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("=" * 70 + "\n")
        return True

    if requests is None:
        log.error("The 'requests' package is not installed. Please run: pip install requests")
        return False

    session = get_http_session()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        response = session.post(full_url, json=payload, headers=headers, timeout=timeout)
        if response.status_code in (200, 201, 202):
            log.info(f"Successfully posted to {full_url} (HTTP {response.status_code})")
            return True
        else:
            log.warning(f"Backend responded with HTTP {response.status_code} at {full_url}: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        log.warning(f"Backend not reachable at {full_url}. (Will continue and retry next cycle — backend may not be started yet)")
        return False
    except requests.exceptions.Timeout:
        log.warning(f"Request timeout while connecting to {full_url} ({timeout}s)")
        return False
    except requests.exceptions.RequestException as e:
        log.warning(f"HTTP request error posting to {full_url}: {e}")
        return False
    except Exception as e:
        log.error(f"Unexpected error posting to {full_url}: {e}")
        return False
