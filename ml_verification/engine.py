"""
ML/NLP Verification Engine.
Main entry point for classification, duplicate detection, and trust scoring.

Public API:
  classify_and_score(report: dict, recent_events: list[dict], official_readings: list[dict]) -> dict
"""

import sys
from typing import Dict, Any, List, Optional

try:
    from ml_verification.classifier import get_classifier
    from ml_verification.duplicate import detect_duplicate
    from ml_verification.scorer import compute_verification
except ImportError:
    from classifier import get_classifier
    from duplicate import detect_duplicate
    from scorer import compute_verification


def classify_and_score(
    report: Dict[str, Any],
    recent_events: Optional[List[Dict[str, Any]]] = None,
    official_readings: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Classifies a raw report text, checks for semantic duplicates against recent events,
    and calculates the trust score and factor breakdown according to the Shared Technical Contract.

    Parameters:
      report: Dict shaped like RawReport / WeatherEvent input:
        {
          "rawText": str,
          "mediaUrls": list[str] (optional),
          "lat": float (optional),
          "lon": float (optional),
          "city": str (optional),
          "state": str (optional),
          "source": str ("CITIZEN" | "SOCIAL_SIMULATED" | "NEWS_RSS" | "OFFICIAL_STATION"),
          "reportedAt": str ISO timestamp (optional),
          "mediaMeta": dict (optional EXIF metadata)
        }
      recent_events: List of recent WeatherEvent dicts within the time/spatial window.
      official_readings: List of OfficialReading dicts from IMD / official weather stations.

    Returns:
      Dict matching WeatherEvent fields:
        {
          "eventType": "RAINFALL"|"THUNDERSTORM"|"FLOODING"|"HEATWAVE"|"FOG"|"DUST_STORM"|"STRONG_WIND"|"UNKNOWN",
          "classificationConfidence": float (0.0 to 1.0),
          "verificationStatus": "PENDING"|"VERIFIED"|"SUSPICIOUS"|"REJECTED"|"DUPLICATE",
          "trustScore": int (0 to 100),
          "factorBreakdown": {
            "sourceTrust": int,
            "corroborationBoost": int,
            "crossMatchOfficial": int,
            "imageCheck": int
          },
          "corroborationCount": int,
          "duplicateOfId": str or None
        }
    """
    # Safe defensive defaults for inputs
    if not isinstance(report, dict):
        report = {}

    if recent_events is None or not isinstance(recent_events, list):
        recent_events = []

    if official_readings is None or not isinstance(official_readings, list):
        official_readings = []

    try:
        # Step 1: Event Classification
        raw_text = report.get("rawText") or report.get("raw_text") or ""
        classifier = get_classifier()
        event_type, confidence = classifier.classify(raw_text)

        # Step 2: Semantic Duplicate Detection
        # Similarity > 0.85 AND same eventType -> mark DUPLICATE, set duplicateOfId
        is_duplicate, duplicate_of_id, _ = detect_duplicate(
            report=report,
            target_event_type=event_type,
            recent_events=recent_events,
            similarity_threshold=0.85
        )

        # Step 3: Trust Scoring & Verification Status
        verification_result = compute_verification(
            report=report,
            event_type=event_type,
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of_id,
            recent_events=recent_events,
            official_readings=official_readings
        )

        # Construct final output dictionary matching Shared Technical Contract
        return {
            "eventType": event_type,
            "classificationConfidence": round(float(confidence), 3),
            "verificationStatus": verification_result["verificationStatus"],
            "trustScore": int(verification_result["trustScore"]),
            "factorBreakdown": verification_result["factorBreakdown"],
            "corroborationCount": int(verification_result["corroborationCount"]),
            "duplicateOfId": duplicate_of_id
        }

    except Exception as exc:
        # Failsafe fallback: never throw unhandled exception on bad input
        return {
            "eventType": "UNKNOWN",
            "classificationConfidence": 0.0,
            "verificationStatus": "SUSPICIOUS",
            "trustScore": 20,
            "factorBreakdown": {
                "sourceTrust": 40,
                "corroborationBoost": 0,
                "crossMatchOfficial": 0,
                "imageCheck": 0
            },
            "corroborationCount": 0,
            "duplicateOfId": None
        }


def preload_models():
    """
    Preloads ML classification & SentenceTransformer duplicate detection models at startup.
    Executes a dummy pass to warm up PyTorch / SentenceTransformer execution path before accepting traffic.
    """
    import logging
    logger = logging.getLogger("backend.ml_verification")
    logger.info("Preloading ML verification models (Classifier & SentenceTransformer)...")
    try:
        classifier = get_classifier()
        classifier.classify("Warmup rain report text")

        try:
            from ml_verification.duplicate import _get_st_model, get_embedding
        except ImportError:
            from duplicate import _get_st_model, get_embedding

        st_model = _get_st_model()
        if st_model is not None:
            get_embedding("Warmup test report text for duplicate detection")
        logger.info("ML models preloaded, backend ready")
    except Exception as err:
        logger.warning(f"Error during ML model preloading: {err}")

