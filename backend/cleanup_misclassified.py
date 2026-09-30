#!/usr/bin/env python3
"""
cleanup_misclassified.py - One-off cleanup script for Weather Analytics Platform (PS 26069)

Re-evaluates existing NEWS_RSS events in SQLite database using updated ML classification & scoring logic.
If an event fails classification (no weather keywords / low ML confidence):
- eventType -> "UNKNOWN"
- trustScore -> 15
- verificationStatus -> "SUSPICIOUS"
- factorBreakdown -> {"classificationCheck": "Content did not match any recognized weather event pattern (score fixed at 15)"}
"""

import sys
import json
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from ml_verification.engine import classify_and_score
except ImportError:
    from engine import classify_and_score

DB_PATH = BASE_DIR / "weather_platform.db"


def run_cleanup():
    print(f"Connecting to database at: {DB_PATH}")
    if not DB_PATH.exists():
        print("Database file does not exist. Nothing to clean up.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, source, raw_text, city, state, media_urls, reported_at, event_type, verification_status, trust_score
        FROM events
    """)
    rows = cursor.fetchall()
    print(f"Scanning {len(rows)} total weather events in database...")

    all_reports = []
    for r in rows:
        all_reports.append({
            "id": r[0],
            "source": r[1],
            "rawText": r[2],
            "city": r[3],
            "state": r[4],
            "mediaUrls": json.loads(r[5]) if r[5] else [],
            "reportedAt": r[6],
            "eventType": r[7],
            "verificationStatus": r[8],
            "trustScore": r[9]
        })

    updated_count = 0

    for report in all_reports:
        scored = classify_and_score(
            report=report,
            recent_events=all_reports,
            official_readings=[]
        )

        new_event_type = scored["eventType"]
        new_status = scored["verificationStatus"]
        new_score = scored["trustScore"]
        new_breakdown = json.dumps(scored["factorBreakdown"])

        if (
            report["eventType"] != new_event_type or
            report["verificationStatus"] != new_status or
            report["trustScore"] != new_score
        ):
            cursor.execute("""
                UPDATE events
                SET event_type = ?,
                    verification_status = ?,
                    trust_score = ?,
                    factor_breakdown = ?
                WHERE id = ?
            """, (new_event_type, new_status, new_score, new_breakdown, report["id"]))
            updated_count += 1

    conn.commit()
    print(f"Successfully updated {updated_count} misclassified events in place.")

    # Verification query required by Fix Part 4:
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE source = 'NEWS_RSS'
          AND event_type = 'UNKNOWN'
          AND verification_status != 'SUSPICIOUS'
    """)
    bad_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE source = 'NEWS_RSS' AND event_type = 'UNKNOWN' AND verification_status = 'SUSPICIOUS'
    """)
    suspicious_count = cursor.fetchone()[0]

    print(f"\nVerification Results:")
    print(f" - NEWS_RSS UNKNOWN events set to SUSPICIOUS: {suspicious_count}")
    print(f" - NEWS_RSS UNKNOWN events with status OTHER than SUSPICIOUS: {bad_count}")

    if bad_count == 0:
        print("[SUCCESS] CONFIRMED: 0 misclassified NEWS_RSS events remain above SUSPICIOUS status!")
    else:
        print(f"[WARNING] Found {bad_count} events still above SUSPICIOUS status.")

    conn.close()


if __name__ == "__main__":
    run_cleanup()
