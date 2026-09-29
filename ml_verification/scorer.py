"""
Trust Scoring & Verification Engine.
Implements the exact Verification Scoring Formula from Shared Technical Contract:
- sourceTrust: OFFICIAL_STATION=100, NEWS_RSS=75, CITIZEN=50, SOCIAL_SIMULATED=40
- corroborationBoost: +5 per independent same-eventType report in same city within 3h, capped at +30
- crossMatchOfficial: matches official reading -> +15
                      contradicts official reading -> -40
                      no official data available -> +0
- imageCheck: media present + EXIF/timestamp plausible -> +10
              media present + implausible/missing EXIF -> -10
              no media -> +0

trustScore = clamp(sum, 0, 100)
Status thresholds:
>= 70 -> VERIFIED | 40-69 -> PENDING | < 40 -> SUSPICIOUS
(or DUPLICATE if flagged by duplicate detector)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


SOURCE_TRUST_MAP = {
    "OFFICIAL_STATION": 100,
    "NEWS_RSS": 75,
    "CITIZEN": 50,
    "SOCIAL_REAL": 45,
    "SOCIAL_SIMULATED": 40
}


def _parse_timestamp(ts_str: Any) -> Optional[datetime]:
    """Safely parses ISO timestamp strings or datetime objects."""
    if not ts_str:
        return None
    if isinstance(ts_str, datetime):
        return ts_str if ts_str.tzinfo else ts_str.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def calculate_source_trust(source: str) -> int:
    """Returns trust score for the report source."""
    if not source:
        return 50
    normalized = str(source).strip().upper()
    return SOURCE_TRUST_MAP.get(normalized, 50)


def calculate_corroboration(
    report: Dict[str, Any],
    event_type: str,
    recent_events: List[Dict[str, Any]]
) -> tuple[int, int]:
    """
    Computes corroboration count and boost:
    +5 per independent same-eventType report in same city within 3h, capped at +30.
    Returns: (corroborationBoost, corroborationCount)
    """
    if not recent_events or not isinstance(recent_events, list):
        return 0, 0

    report_city = str(report.get("city") or "").strip().lower()
    report_id = str(report.get("id") or "")
    report_time = _parse_timestamp(report.get("reportedAt") or report.get("reported_at"))

    corroboration_count = 0

    for event in recent_events:
        if not isinstance(event, dict):
            continue

        # Skip self
        cand_id = str(event.get("id") or "")
        if report_id and cand_id and report_id == cand_id:
            continue

        # Skip if candidate itself is a duplicate
        if event.get("duplicateOfId") or event.get("verificationStatus") == "DUPLICATE":
            continue

        # Must match same eventType
        if event.get("eventType") != event_type:
            continue

        # Must match same city (case-insensitive)
        cand_city = str(event.get("city") or "").strip().lower()
        if report_city and cand_city:
            if report_city != cand_city:
                continue
        elif report.get("state") and event.get("state"):
            if str(report.get("state")).strip().lower() != str(event.get("state")).strip().lower():
                continue

        # Check timestamp proximity within 3 hours (10,800 seconds) if timestamps exist
        cand_time = _parse_timestamp(event.get("reportedAt") or event.get("reported_at") or event.get("ingestedAt"))
        if report_time and cand_time:
            time_diff = abs((report_time - cand_time).total_seconds())
            if time_diff > 3 * 3600:
                continue

        corroboration_count += 1

    boost = min(30, corroboration_count * 5)
    return boost, corroboration_count


def evaluate_official_cross_match(
    report: Dict[str, Any],
    event_type: str,
    official_readings: List[Dict[str, Any]]
) -> int:
    """
    Cross-matches report with official station readings:
      Matches official reading -> +15
      Contradicts official reading -> -40
      No official data available -> +0
    """
    if not official_readings or not isinstance(official_readings, list):
        return 0

    report_city = str(report.get("city") or "").strip().lower()
    report_state = str(report.get("state") or "").strip().lower()

    # Find closest matching official reading for this city/state
    matched_reading = None
    for r in official_readings:
        if not isinstance(r, dict):
            continue
        read_city = str(r.get("city") or "").strip().lower()
        read_state = str(r.get("state") or "").strip().lower()

        if report_city and read_city and report_city == read_city:
            matched_reading = r
            break
        elif report_state and read_state and report_state == read_state:
            matched_reading = r

    if not matched_reading:
        return 0

    condition = str(matched_reading.get("condition") or "").lower()
    try:
        rainfall_mm = float(matched_reading.get("rainfallMm", 0.0) or 0.0)
    except (ValueError, TypeError):
        rainfall_mm = 0.0

    try:
        temp_c = float(matched_reading.get("tempC", 25.0) or 25.0)
    except (ValueError, TypeError):
        temp_c = 25.0

    try:
        wind_kph = float(matched_reading.get("windKph", 10.0) or 10.0)
    except (ValueError, TypeError):
        wind_kph = 10.0

    # Cross-match evaluation per category
    if event_type == "RAINFALL":
        if rainfall_mm >= 1.0 or any(w in condition for w in ["rain", "shower", "drizzle", "monsoon"]):
            return 15
        if rainfall_mm == 0.0 and any(w in condition for w in ["clear", "sunny", "dry", "heatwave", "fair"]):
            return -40

    elif event_type == "FLOODING":
        if rainfall_mm >= 15.0 or "flood" in condition or "heavy rain" in condition:
            return 15
        if rainfall_mm == 0.0 and any(w in condition for w in ["clear", "sunny", "dry", "fair"]):
            return -40

    elif event_type == "THUNDERSTORM":
        if any(w in condition for w in ["thunder", "lightning", "storm", "squall"]) or (rainfall_mm >= 5.0 and wind_kph >= 30.0):
            return 15
        if any(w in condition for w in ["clear", "sunny", "calm"]) and rainfall_mm == 0.0 and wind_kph < 15.0:
            return -40

    elif event_type == "HEATWAVE":
        if temp_c >= 40.0 or any(w in condition for w in ["heatwave", "hot", "very hot"]):
            return 15
        if temp_c < 32.0 or rainfall_mm >= 5.0 or any(w in condition for w in ["rain", "cold", "thunderstorm"]):
            return -40

    elif event_type == "FOG":
        if any(w in condition for w in ["fog", "mist", "haze", "smog"]):
            return 15
        if any(w in condition for w in ["clear", "sunny"]) and temp_c >= 28.0:
            return -40

    elif event_type == "DUST_STORM":
        if any(w in condition for w in ["dust", "sandstorm", "haboob"]) or (wind_kph >= 35.0 and temp_c >= 30.0):
            return 15
        if rainfall_mm >= 5.0 or wind_kph < 10.0:
            return -40

    elif event_type == "STRONG_WIND":
        if wind_kph >= 40.0 or any(w in condition for w in ["gale", "windy", "squall", "storm"]):
            return 15
        if wind_kph < 15.0 and any(w in condition for w in ["calm", "clear", "light breeze"]):
            return -40

    return 0


def evaluate_image_check(report: Dict[str, Any]) -> int:
    """
    Evaluates media presence and EXIF plausibility:
      Media present + EXIF/timestamp plausible -> +10
      Media present + implausible/missing EXIF -> -10
      No media -> +0

    NOTE: Full image forensics / deep-learning verification is a future milestone.
    This module implements the v1 signal based on EXIF presence and timestamp plausibility.
    """
    media_urls = report.get("mediaUrls") or report.get("media_urls") or []
    if not media_urls or not isinstance(media_urls, list) or len(media_urls) == 0:
        return 0

    # Media is present: inspect metadata for EXIF plausibility
    # Check mediaMeta, sourceMeta, or exif dictionaries attached to report
    meta = (
        report.get("mediaMeta")
        or report.get("media_meta")
        or report.get("exif")
        or report.get("sourceMeta", {}).get("media")
        or {}
    )

    # 1. Explicit boolean flag if caller already parsed EXIF
    if meta.get("exifPlausible") is True or meta.get("exif_plausible") is True:
        return 10
    if meta.get("exifPlausible") is False or meta.get("exif_plausible") is False:
        return -10

    # 2. Check EXIF timestamp plausibility relative to reportedAt
    exif_time = _parse_timestamp(meta.get("dateTimeOriginal") or meta.get("exifTimestamp"))
    report_time = _parse_timestamp(report.get("reportedAt") or report.get("reported_at"))

    if exif_time and report_time:
        diff_hours = abs((report_time - exif_time).total_seconds()) / 3600.0
        # If photo timestamp is within 24 hours of report, plausible
        if diff_hours <= 24.0:
            return 10
        else:
            return -10

    # If hasExif is explicitly False or no EXIF metadata provided at all -> missing EXIF (-10)
    if meta.get("hasExif") is True:
        return 10

    return -10


def compute_verification(
    report: Dict[str, Any],
    event_type: str,
    is_duplicate: bool,
    duplicate_of_id: Optional[str],
    recent_events: List[Dict[str, Any]],
    official_readings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculates the full factorBreakdown, trustScore, and verificationStatus.
    Returns:
      {
        "trustScore": int,
        "verificationStatus": str,
        "factorBreakdown": {
          "sourceTrust": int,
          "corroborationBoost": int,
          "crossMatchOfficial": int,
          "imageCheck": int
        },
        "corroborationCount": int
      }
    """
    source = report.get("source") or "CITIZEN"
    source_trust = calculate_source_trust(source)

    corrob_boost, corrob_count = calculate_corroboration(report, event_type, recent_events)
    official_match = evaluate_official_cross_match(report, event_type, official_readings)
    img_check = evaluate_image_check(report)

    factor_breakdown = {
        "sourceTrust": source_trust,
        "corroborationBoost": corrob_boost,
        "crossMatchOfficial": official_match,
        "imageCheck": img_check
    }

    raw_sum = source_trust + corrob_boost + official_match + img_check
    trust_score = max(0, min(100, raw_sum))

    if is_duplicate:
        verification_status = "DUPLICATE"
    elif event_type == "UNKNOWN":
        trust_score = min(trust_score, 25)
        verification_status = "SUSPICIOUS"
    elif trust_score >= 70:
        verification_status = "VERIFIED"
    elif trust_score >= 40:
        verification_status = "PENDING"
    else:
        verification_status = "SUSPICIOUS"

    return {
        "trustScore": trust_score,
        "verificationStatus": verification_status,
        "factorBreakdown": factor_breakdown,
        "corroborationCount": corrob_count
    }
