"""
Standalone Test Suite for ML Verification Engine.
Runs 10 comprehensive test scenarios demonstrating:
  1. All 7 WeatherEvent categories (RAINFALL, THUNDERSTORM, FLOODING, HEATWAVE, FOG, DUST_STORM, STRONG_WIND)
  2. Hindi Devanagari and Hinglish transliteration classification
  3. Semantic duplicate detection (>0.85 cosine similarity + same eventType)
  4. Official reading match (+15) and contradiction (-40)
  5. Media EXIF plausibility (+10) and missing/implausible EXIF (-10)
  6. Corroboration boost calculation (+5 per independent report, up to +30)
  7. Edge case and malformed input resilience

Run via:
  python test_standalone.py
"""

import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add current folder to sys.path so it works identically whether run standalone or as a package
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from engine import classify_and_score


def run_tests():
    print("=" * 80)
    print("  STANDALONE VERIFICATION TEST SUITE (National Weather Big Data Analytics)")
    print("=" * 80)

    # Mock Official Station Readings (shaped per Shared Technical Contract)
    official_readings = [
        {
            "id": "off-mumbai-01",
            "city": "Mumbai",
            "state": "Maharashtra",
            "lat": 19.0760,
            "lon": 72.8777,
            "recordedAt": "2026-09-27T14:00:00Z",
            "condition": "Heavy Rain",
            "rainfallMm": 42.5,
            "tempC": 26.5,
            "windKph": 28.0
        },
        {
            "id": "off-delhi-01",
            "city": "Delhi",
            "state": "Delhi",
            "lat": 28.6139,
            "lon": 77.2090,
            "recordedAt": "2026-09-27T14:00:00Z",
            "condition": "Dense Fog",
            "rainfallMm": 0.0,
            "tempC": 12.0,
            "windKph": 6.0
        },
        {
            "id": "off-nagpur-01",
            "city": "Nagpur",
            "state": "Maharashtra",
            "lat": 21.1458,
            "lon": 79.0882,
            "recordedAt": "2026-09-27T14:00:00Z",
            "condition": "Heatwave",
            "rainfallMm": 0.0,
            "tempC": 45.8,
            "windKph": 14.0
        },
        {
            "id": "off-jaipur-01",
            "city": "Jaipur",
            "state": "Rajasthan",
            "lat": 26.9124,
            "lon": 75.7873,
            "recordedAt": "2026-09-27T14:00:00Z",
            "condition": "Dust Storm",
            "rainfallMm": 0.0,
            "tempC": 38.0,
            "windKph": 48.0
        },
        {
            "id": "off-pune-01",
            "city": "Pune",
            "state": "Maharashtra",
            "lat": 18.5204,
            "lon": 73.8567,
            "recordedAt": "2026-09-27T14:00:00Z",
            "condition": "Clear",
            "rainfallMm": 0.0,
            "tempC": 27.0,
            "windKph": 8.0
        },
        {
            "id": "off-shimla-01",
            "city": "Shimla",
            "state": "Himachal Pradesh",
            "lat": 31.1048,
            "lon": 77.1734,
            "recordedAt": "2026-09-27T14:00:00Z",
            "condition": "Rainfall",
            "rainfallMm": 18.0,
            "tempC": 14.0,
            "windKph": 12.0
        }
    ]

    # Mock Recent Events (shaped per Shared Technical Contract)
    recent_events = [
        {
            "id": "evt-mumbai-flood-01",
            "source": "CITIZEN",
            "rawText": "Waterlogging at Hindmata cinema junction, knee-deep flood waters.",
            "mediaUrls": ["https://storage.weather.gov.in/media/img1.jpg"],
            "reportedAt": "2026-09-27T13:30:00Z",
            "city": "Mumbai",
            "state": "Maharashtra",
            "eventType": "FLOODING",
            "verificationStatus": "VERIFIED",
            "trustScore": 75
        },
        {
            "id": "evt-mumbai-flood-02",
            "source": "CITIZEN",
            "rawText": "Severe waterlogging near Dadar TT circle, vehicles stuck.",
            "mediaUrls": [],
            "reportedAt": "2026-09-27T13:45:00Z",
            "city": "Mumbai",
            "state": "Maharashtra",
            "eventType": "FLOODING",
            "verificationStatus": "VERIFIED",
            "trustScore": 70
        },
        {
            "id": "evt-mumbai-flood-03",
            "source": "NEWS_RSS",
            "rawText": "Mumbai rains: Heavy water stagnation reported along Western Express Highway.",
            "mediaUrls": [],
            "reportedAt": "2026-09-27T13:15:00Z",
            "city": "Mumbai",
            "state": "Maharashtra",
            "eventType": "FLOODING",
            "verificationStatus": "VERIFIED",
            "trustScore": 85
        }
    ]

    # Test Scenarios
    scenarios = [
        {
            "name": "1. RAINFALL (Official Station, Plausible EXIF, Official Match)",
            "report": {
                "source": "OFFICIAL_STATION",
                "rawText": "Heavy continuous rainfall recorded across South Mumbai colaba observatory.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "mediaUrls": ["https://storage.weather.gov.in/obs/rain_gauge.jpg"],
                "reportedAt": "2026-09-27T14:10:00Z",
                "mediaMeta": {"exifPlausible": True}
            },
            "expected_status": "VERIFIED",
            "expected_event": "RAINFALL"
        },
        {
            "name": "2. FLOODING (Citizen Report with Multi-Event Corroboration + Match)",
            "report": {
                "source": "CITIZEN",
                "rawText": "Massive waterlogging in lower parel, streets completely flooded and submerged.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "mediaUrls": ["https://storage.weather.gov.in/citizen/flood_street.jpg"],
                "reportedAt": "2026-09-27T14:05:00Z",
                "mediaMeta": {"exifPlausible": True}
            },
            "expected_status": "VERIFIED",
            "expected_event": "FLOODING"
        },
        {
            "name": "3. THUNDERSTORM (Hindi Devanagari + News RSS)",
            "report": {
                "source": "NEWS_RSS",
                "rawText": "भीषण आंधी-तूफान के साथ आकाशीय बिजली चमकी, बादलों की तेज गर्जना जारी।",
                "city": "Kolkata",
                "state": "West Bengal",
                "mediaUrls": [],
                "reportedAt": "2026-09-27T14:00:00Z"
            },
            "expected_status": "VERIFIED",
            "expected_event": "THUNDERSTORM"
        },
        {
            "name": "4. HEATWAVE (Hinglish Transliteration + Simulated Social Feed)",
            "report": {
                "source": "SOCIAL_SIMULATED",
                "rawText": "Nagpur me bohot bhayankar garmi pad rahi hai aur tez loo chal rahi hai bahar 46 degree.",
                "city": "Nagpur",
                "state": "Maharashtra",
                "mediaUrls": [],
                "reportedAt": "2026-09-27T14:00:00Z"
            },
            "expected_status": "PENDING",
            "expected_event": "HEATWAVE"
        },
        {
            "name": "5. FOG (Missing EXIF Penalty -10)",
            "report": {
                "source": "CITIZEN",
                "rawText": "Dense fog shrouding IGI Airport runway, zero visibility this morning.",
                "city": "Delhi",
                "state": "Delhi",
                "mediaUrls": ["https://storage.weather.gov.in/citizen/fog_delhi.jpg"],
                "reportedAt": "2026-09-27T14:00:00Z",
                "mediaMeta": {"hasExif": False}  # Missing EXIF -> -10
            },
            "expected_status": "PENDING",
            "expected_event": "FOG"
        },
        {
            "name": "6. DUST_STORM (Valid Media EXIF +10)",
            "report": {
                "source": "CITIZEN",
                "rawText": "Massive dust storm and blinding sand gale swept through Jaipur outskirts.",
                "city": "Jaipur",
                "state": "Rajasthan",
                "mediaUrls": ["https://storage.weather.gov.in/citizen/sandstorm.jpg"],
                "reportedAt": "2026-09-27T14:00:00Z",
                "mediaMeta": {"exifPlausible": True}  # Valid EXIF -> +10
            },
            "expected_status": "VERIFIED",
            "expected_event": "DUST_STORM"
        },
        {
            "name": "7. STRONG_WIND (Contradicts Official Calm Reading -> -40 Penalty)",
            "report": {
                "source": "CITIZEN",
                "rawText": "Violent windstorm and gale force winds uprooting large trees in Pune city!",
                "city": "Pune",
                "state": "Maharashtra",
                "mediaUrls": [],
                "reportedAt": "2026-09-27T14:00:00Z"
            },
            "expected_status": "SUSPICIOUS",
            "expected_event": "STRONG_WIND"
        },
        {
            "name": "8. DUPLICATE DETECTION (Cosine Similarity > 0.85 to Prior Report)",
            "report": {
                "source": "CITIZEN",
                "rawText": "Waterlogging at Hindmata cinema junction, knee-deep flood waters.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "mediaUrls": [],
                "reportedAt": "2026-09-27T14:15:00Z"
            },
            "expected_status": "DUPLICATE",
            "expected_event": "FLOODING"
        },
        {
            "name": "9. DELIBERATELY FAKE / IMPLAUSIBLE (Heatwave in Cold Rainy Shimla)",
            "report": {
                "source": "SOCIAL_SIMULATED",
                "rawText": "Unbearable 48 degree scorching heatwave and burning sun in Shimla mall road!",
                "city": "Shimla",
                "state": "Himachal Pradesh",
                "mediaUrls": ["https://storage.weather.gov.in/fake/sun.jpg"],
                "reportedAt": "2026-09-27T14:00:00Z",
                "mediaMeta": {"exifPlausible": False}  # Fake/mismatched EXIF -> -10
            },
            "expected_status": "SUSPICIOUS",
            "expected_event": "HEATWAVE"
        },
        {
            "name": "10. RESILIENCE / EDGE CASE (Empty & Malformed Payload)",
            "report": {
                "rawText": "",
                "source": None,
                "city": None,
                "mediaUrls": None
            },
            "expected_status": "SUSPICIOUS",
            "expected_event": "UNKNOWN"
        }
    ]

    passed_count = 0

    for idx, test in enumerate(scenarios, 1):
        print(f"\n--- Scenario {idx}: {test['name']} ---")
        output = classify_and_score(
            report=test["report"],
            recent_events=recent_events,
            official_readings=official_readings
        )

        fb = output["factorBreakdown"]
        print(f"  * Text:            \"{test['report'].get('rawText', '')[:65]}...\"" if test['report'].get('rawText') else "  * Text:            <EMPTY>")
        print(f"  * Classified As:   {output['eventType']} (Confidence: {output['classificationConfidence']:.2f})")
        print(f"  * Status:          {output['verificationStatus']}")
        print(f"  * Trust Score:     {output['trustScore']}/100")
        print(f"  * Breakdown:       SourceTrust: {fb['sourceTrust']} | CorrobBoost: +{fb['corroborationBoost']} | OfficialMatch: {fb['crossMatchOfficial']} | ImageCheck: {fb['imageCheck']}")
        print(f"  * Corroborations:  {output['corroborationCount']}")
        print(f"  * DuplicateOfId:   {output['duplicateOfId']}")

        # Validate contract compliance
        assert "eventType" in output, "Missing eventType"
        assert "classificationConfidence" in output, "Missing classificationConfidence"
        assert "verificationStatus" in output, "Missing verificationStatus"
        assert "trustScore" in output, "Missing trustScore"
        assert "factorBreakdown" in output, "Missing factorBreakdown"
        assert "corroborationCount" in output, "Missing corroborationCount"
        assert "duplicateOfId" in output, "Missing duplicateOfId"
        assert 0 <= output["trustScore"] <= 100, f"Trust score out of bounds: {output['trustScore']}"

        # Match check
        status_match = (output["verificationStatus"] == test["expected_status"])
        event_match = (output["eventType"] == test["expected_event"])

        if status_match and event_match:
            passed_count += 1
            print("  --> [PASS]")
        else:
            print(f"  --> [FAIL] Expected ({test['expected_event']}, {test['expected_status']}), got ({output['eventType']}, {output['verificationStatus']})")

    print("\n" + "=" * 80)
    print(f"  SUMMARY: {passed_count}/{len(scenarios)} Test Scenarios Passed Successfully.")
    print("=" * 80)
    return passed_count == len(scenarios)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
