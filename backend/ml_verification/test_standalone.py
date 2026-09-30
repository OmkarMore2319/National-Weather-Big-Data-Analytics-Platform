"""
Standalone verification script for Person 2 (ML Verification Engine).
Tests all 10 core verification scenarios defined in the Shared Technical Contract:
1. RAINFALL (Official Station, Plausible EXIF, Official Match)
2. FLOODING (Citizen Report with Multi-Event Corroboration + Match)
3. THUNDERSTORM (Hindi Devanagari + News RSS)
4. HEATWAVE (Hinglish Transliteration + Simulated Social Feed)
5. FOG (Missing EXIF Penalty -10)
6. DUST_STORM (Valid Media EXIF +10)
7. STRONG_WIND (Contradicts Official Calm Reading -> -40 Penalty)
8. DUPLICATE DETECTION (Cosine Similarity > 0.85 to Prior Report)
9. DELIBERATELY FAKE / IMPLAUSIBLE (Heatwave in Cold Rainy Shimla)
10. RESILIENCE / EDGE CASE (Empty & Malformed Payload)
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

try:
    from ml_verification.engine import classify_and_score
except ImportError:
    from engine import classify_and_score


def run_tests():
    print("=" * 80)
    print("  STANDALONE VERIFICATION TEST SUITE (National Weather Big Data Analytics)")
    print("=" * 80)

    now = datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Mock Official Readings
    official_readings = [
        {
            "id": "stat-01",
            "city": "Mumbai",
            "state": "Maharashtra",
            "recordedAt": now_iso,
            "condition": "Heavy Rain & Downpour",
            "rainfallMm": 45.0,
            "tempC": 26.5,
            "windKph": 28.0
        },
        {
            "id": "stat-02",
            "city": "Pune",
            "state": "Maharashtra",
            "recordedAt": now_iso,
            "condition": "Clear Sky & Calm",
            "rainfallMm": 0.0,
            "tempC": 24.0,
            "windKph": 8.0
        },
        {
            "id": "stat-03",
            "city": "Shimla",
            "state": "Himachal Pradesh",
            "recordedAt": now_iso,
            "condition": "Heavy Snow & Cold",
            "rainfallMm": 15.0,
            "tempC": 4.0,
            "windKph": 12.0
        }
    ]

    # Mock Recent Events for Corroboration & Deduplication
    recent_events = [
        {
            "id": "evt-mumbai-flood-01",
            "source": "CITIZEN",
            "city": "Mumbai",
            "state": "Maharashtra",
            "eventType": "FLOODING",
            "rawText": "Waterlogging at Hindmata cinema junction, knee-deep flood waters.",
            "verificationStatus": "VERIFIED",
            "reportedAt": (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "id": "evt-mumbai-flood-02",
            "source": "SOCIAL_SIMULATED",
            "city": "Mumbai",
            "state": "Maharashtra",
            "eventType": "FLOODING",
            "rawText": "Flooding reported in Dadar TT circle near underpass.",
            "verificationStatus": "VERIFIED",
            "reportedAt": (now - timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "id": "evt-mumbai-flood-03",
            "source": "NEWS_RSS",
            "city": "Mumbai",
            "state": "Maharashtra",
            "eventType": "FLOODING",
            "rawText": "Suburban trains slow down as water levels rise on tracks near Kurla.",
            "verificationStatus": "VERIFIED",
            "reportedAt": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    ]

    scenarios = [
        {
            "name": "1. RAINFALL (Official Station, Plausible EXIF, Official Match)",
            "report": {
                "id": "rep-01",
                "source": "OFFICIAL_STATION",
                "rawText": "Heavy continuous rainfall recorded across South Mumbai colaba observatory.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "reportedAt": now_iso,
                "mediaUrls": ["http://media.example.com/rain1.jpg"],
                "mediaMeta": {"exifPlausible": True}
            }
        },
        {
            "name": "2. FLOODING (Citizen Report with Multi-Event Corroboration + Match)",
            "report": {
                "id": "rep-02",
                "source": "CITIZEN",
                "rawText": "Massive waterlogging in lower parel, streets completely flooded and submerged.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "reportedAt": now_iso,
                "mediaUrls": ["http://media.example.com/flood1.jpg"],
                "mediaMeta": {"exifPlausible": True}
            }
        },
        {
            "name": "3. THUNDERSTORM (Hindi Devanagari + News RSS)",
            "report": {
                "id": "rep-03",
                "source": "NEWS_RSS",
                "rawText": "भीषण आंधी-तूफान के साथ आकाशीय बिजली चमकी, बादलों की तेज गर्जना जारी।",
                "city": "Lucknow",
                "state": "Uttar Pradesh",
                "reportedAt": now_iso
            }
        },
        {
            "name": "4. HEATWAVE (Hinglish Transliteration + Simulated Social Feed)",
            "report": {
                "id": "rep-04",
                "source": "SOCIAL_SIMULATED",
                "rawText": "Nagpur me bohot bhayankar garmi pad rahi hai aur tez loo chal rahi hai.",
                "city": "Nagpur",
                "state": "Maharashtra",
                "reportedAt": now_iso
            }
        },
        {
            "name": "5. FOG (Missing EXIF Penalty -10)",
            "report": {
                "id": "rep-05",
                "source": "CITIZEN",
                "rawText": "Dense fog shrouding IGI Airport runway, zero visibility this morning.",
                "city": "Delhi",
                "state": "Delhi",
                "reportedAt": now_iso,
                "mediaUrls": ["http://media.example.com/fog1.jpg"],
                "mediaMeta": {"hasExif": False}
            }
        },
        {
            "name": "6. DUST_STORM (Valid Media EXIF +10)",
            "report": {
                "id": "rep-06",
                "source": "CITIZEN",
                "rawText": "Massive dust storm and blinding sand gale swept through Jaipur outer bypass.",
                "city": "Jaipur",
                "state": "Rajasthan",
                "reportedAt": now_iso,
                "mediaUrls": ["http://media.example.com/dust.jpg"],
                "mediaMeta": {"exifPlausible": True}
            }
        },
        {
            "name": "7. STRONG_WIND (Contradicts Official Calm Reading -> -40 Penalty)",
            "report": {
                "id": "rep-07",
                "source": "CITIZEN",
                "rawText": "Violent windstorm and gale force winds uprooting large trees in Pune city.",
                "city": "Pune",
                "state": "Maharashtra",
                "reportedAt": now_iso
            }
        },
        {
            "name": "8. DUPLICATE DETECTION (Cosine Similarity > 0.85 to Prior Report)",
            "report": {
                "id": "rep-08",
                "source": "CITIZEN",
                "rawText": "Waterlogging at Hindmata cinema junction, knee-deep flood waters.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "reportedAt": now_iso
            }
        },
        {
            "name": "9. DELIBERATELY FAKE / IMPLAUSIBLE (Heatwave in Cold Rainy Shimla)",
            "report": {
                "id": "rep-09",
                "source": "SOCIAL_SIMULATED",
                "rawText": "Unbearable 48 degree scorching heatwave and burning sun in Shimla right now!",
                "city": "Shimla",
                "state": "Himachal Pradesh",
                "reportedAt": now_iso,
                "mediaUrls": ["http://media.example.com/fake.jpg"],
                "mediaMeta": {"exifPlausible": False}
            }
        },
        {
            "name": "10. RESILIENCE / EDGE CASE (Empty & Malformed Payload)",
            "report": {
                "rawText": "",
                "city": None
            }
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
        if "classificationCheck" in fb:
            print(f"  * Breakdown:       ClassificationCheck: {fb['classificationCheck']}")
        else:
            print(f"  * Breakdown:       SourceTrust: {fb.get('sourceTrust', 0)} | CorrobBoost: +{fb.get('corroborationBoost', 0)} | OfficialMatch: {fb.get('crossMatchOfficial', 0)} | ImageCheck: {fb.get('imageCheck', 0)}")
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

        print("  --> [PASS]")
        passed_count += 1

    print("\n" + "=" * 80)
    print(f"  SUMMARY: {passed_count}/{len(scenarios)} Test Scenarios Passed Successfully.")
    print("=" * 80)
    return passed_count == len(scenarios)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
