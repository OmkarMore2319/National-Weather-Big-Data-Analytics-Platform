import os
import sys
import unittest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure ADMIN_TOKEN is set for test
os.environ["ADMIN_TOKEN"] = "test-secret-token"

from main import app, ADMIN_TOKEN
from database import init_db


class BackendTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_health_check(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_02_get_events_list(self):
        response = self.client.get("/api/v1/events?page=1&pageSize=10")
        self.assertEqual(response.status_code, 200)
        events = response.json()
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)

        # Verify camelCase contract fields
        first = next((e for e in events if e.get("factorBreakdown") and len(e["factorBreakdown"]) > 0), events[0])
        expected_keys = [
            "id", "source", "rawText", "mediaUrls", "reportedAt", "ingestedAt",
            "lat", "lon", "city", "state", "eventType", "classificationConfidence",
            "verificationStatus", "trustScore", "factorBreakdown", "corroborationCount",
            "duplicateOfId", "sourceMeta"
        ]
        for key in expected_keys:
            self.assertIn(key, first, f"Missing expected camelCase key: {key}")

        # Verify factorBreakdown structure
        fb = first["factorBreakdown"]
        self.assertIn("sourceTrust", fb)
        self.assertIn("corroborationBoost", fb)
        self.assertIn("crossMatchOfficial", fb)
        self.assertIn("imageCheck", fb)

    def test_03_events_filtering(self):
        # Filter by eventType
        response = self.client.get("/api/v1/events?eventType=RAINFALL")
        self.assertEqual(response.status_code, 200)
        events = response.json()
        for ev in events:
            self.assertEqual(ev["eventType"], "RAINFALL")

        # Filter by state
        response = self.client.get("/api/v1/events?state=Maharashtra")
        self.assertEqual(response.status_code, 200)
        events = response.json()
        for ev in events:
            self.assertEqual(ev["state"].lower(), "maharashtra")

    def test_04_get_single_event(self):
        list_res = self.client.get("/api/v1/events?pageSize=1")
        first_event = list_res.json()[0]
        ev_id = first_event["id"]

        response = self.client.get(f"/api/v1/events/{ev_id}")
        self.assertEqual(response.status_code, 200)
        ev = response.json()
        self.assertEqual(ev["id"], ev_id)
        self.assertIn("factorBreakdown", ev)

        # Test non-existent ID
        not_found = self.client.get("/api/v1/events/00000000-0000-0000-0000-000000000000")
        self.assertEqual(not_found.status_code, 404)

    def test_05_citizen_report_consent_and_validation(self):
        # Reject without consent
        payload_no_consent = {
            "rawText": "Heavy rains flooding Dadar flower market",
            "mediaUrls": ["https://example.com/img.jpg"],
            "lat": 19.0178,
            "lon": 72.8478,
            "city": "Mumbai",
            "state": "Maharashtra",
            "consentGiven": False,
        }
        res = self.client.post("/api/v1/reports/citizen", json=payload_no_consent)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Consent", res.json()["detail"])

        # Invalid lat/lon
        payload_bad_coords = {
            **payload_no_consent,
            "consentGiven": True,
            "lat": 120.0,  # Invalid (>90)
        }
        res_coords = self.client.post("/api/v1/reports/citizen", json=payload_bad_coords)
        self.assertEqual(res_coords.status_code, 422)

        # Valid submission
        valid_payload = {
            "rawText": "Heavy downpour and waterlogging at Andheri subway",
            "mediaUrls": ["https://example.com/andheri.jpg"],
            "lat": 19.1197,
            "lon": 72.8468,
            "city": "Mumbai",
            "state": "Maharashtra",
            "consentGiven": True,
        }
        res_valid = self.client.post("/api/v1/reports/citizen", json=valid_payload)
        self.assertEqual(res_valid.status_code, 201)
        created = res_valid.json()
        self.assertEqual(created["source"], "CITIZEN")
        self.assertEqual(created["eventType"], "FLOODING")
        self.assertIn("factorBreakdown", created)
        self.assertGreaterEqual(created["trustScore"], 0)
        self.assertLessEqual(created["trustScore"], 100)

    def test_06_internal_ingest(self):
        internal_payload = {
            "rawText": "Severe dust storm approaching Bikaner city with 60 kmph winds",
            "mediaUrls": [],
            "lat": 28.0229,
            "lon": 73.3119,
            "city": "Bikaner",
            "state": "Rajasthan",
            "source": "NEWS_RSS",
            "sourceMeta": {"feed": "DD_Rajasthan", "urgency": "HIGH"},
        }
        res = self.client.post("/api/v1/ingest/internal", json=internal_payload)
        self.assertEqual(res.status_code, 201)
        created = res.json()
        self.assertEqual(created["source"], "NEWS_RSS")
        self.assertEqual(created["eventType"], "DUST_STORM")
        self.assertEqual(created["sourceMeta"]["feed"], "DD_Rajasthan")

    def test_07_admin_override_authentication(self):
        list_res = self.client.get("/api/v1/events?pageSize=1")
        target_event = list_res.json()[0]
        ev_id = target_event["id"]

        override_payload = {
            "adminUsername": "super_admin",
            "newStatus": "VERIFIED",
            "reason": "Satellite Doppler radar confirmation obtained",
        }

        # 1. No token -> 401
        res_no_token = self.client.post(f"/api/v1/admin/events/{ev_id}/override", json=override_payload)
        self.assertEqual(res_no_token.status_code, 401)

        # 2. Invalid token -> 401
        res_bad_token = self.client.post(
            f"/api/v1/admin/events/{ev_id}/override",
            json=override_payload,
            headers={"X-Admin-Token": "wrong-secret-token"},
        )
        self.assertEqual(res_bad_token.status_code, 401)

        # 3. Valid token -> 200
        res_ok = self.client.post(
            f"/api/v1/admin/events/{ev_id}/override",
            json=override_payload,
            headers={"X-Admin-Token": "test-secret-token"},
        )
        self.assertEqual(res_ok.status_code, 200)
        override = res_ok.json()
        self.assertEqual(override["eventId"], ev_id)
        self.assertEqual(override["newStatus"], "VERIFIED")
        self.assertEqual(override["adminUsername"], "super_admin")

        # Verify event verification status actually changed in DB
        ev_check = self.client.get(f"/api/v1/events/{ev_id}").json()
        self.assertEqual(ev_check["verificationStatus"], "VERIFIED")

    def test_08_admin_audit_log(self):
        res = self.client.get("/api/v1/admin/audit-log")
        self.assertEqual(res.status_code, 200)
        logs = res.json()
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)
        first_log = logs[0]
        self.assertIn("adminUsername", first_log)
        self.assertIn("oldStatus", first_log)
        self.assertIn("newStatus", first_log)
        self.assertIn("reason", first_log)
        self.assertIn("timestamp", first_log)

    def test_09_analytics_summary(self):
        res = self.client.get("/api/v1/analytics/summary")
        self.assertEqual(res.status_code, 200)
        summary = res.json()
        self.assertIn("totalToday", summary)
        self.assertIn("pctVerified", summary)
        self.assertIn("topEventType", summary)
        self.assertIn("mostAffectedState", summary)
        self.assertIn("byEventType", summary)
        self.assertIn("byStatus", summary)
        self.assertIsInstance(summary["byEventType"], dict)
        self.assertIsInstance(summary["byStatus"], dict)
        self.assertGreater(summary["totalToday"], 0)

    def test_10_websocket_live(self):
        with self.client.websocket_connect("/ws/live") as websocket:
            # Trigger an internal ingest to generate broadcast
            payload = {
                "rawText": "Sudden thunderstorm over Pune airport",
                "lat": 18.5822,
                "lon": 73.9197,
                "city": "Pune",
                "state": "Maharashtra",
                "source": "CITIZEN",
            }
            res = self.client.post("/api/v1/ingest/internal", json=payload)
            self.assertEqual(res.status_code, 201)

            # Receive WebSocket broadcast wrapped in type="event"
            msg = websocket.receive_json()
            self.assertEqual(msg["type"], "event")
            payload = msg["payload"]
            self.assertEqual(payload["city"], "Pune")
            self.assertEqual(payload["eventType"], "THUNDERSTORM")
            self.assertIn("factorBreakdown", payload)

    def test_11_rate_limiting(self):
        # We test that exceeding 10 requests from the same IP within 1 minute results in HTTP 429
        # Reset limiter for test IP
        from rate_limiter import rate_limiter
        rate_limiter.requests.clear()

        payload = {
            "rawText": "Testing rate limit rapid requests",
            "mediaUrls": [],
            "lat": 19.0760,
            "lon": 72.8777,
            "city": "Mumbai",
            "state": "Maharashtra",
            "consentGiven": True,
        }

        # Send 10 successful requests
        for i in range(10):
            res = self.client.post("/api/v1/reports/citizen", json=payload)
            self.assertEqual(res.status_code, 201)

        # 11th request must fail with 429 Too Many Requests
        res_limit = self.client.post("/api/v1/reports/citizen", json=payload)
        self.assertEqual(res_limit.status_code, 429)
        self.assertIn("Rate limit exceeded", res_limit.json()["detail"])

    def test_12_anomalies_and_threshold_broadcast(self):
        import uuid
        # Clear rate limiter again
        from rate_limiter import rate_limiter
        rate_limiter.requests.clear()

        # Ingest events with distinct reports to cross a threshold of 3 for testing
        test_city = f"TestCity_{uuid.uuid4().hex[:6]}"
        reports = [
            "Severe flooding reported near railway station with submerged tracks",
            "Massive flooding and waterlogging causing traffic gridlock in market",
            "Rising flood waters inundating residential apartments and roads"
        ]
        for text in reports:
            payload = {
                "rawText": text,
                "mediaUrls": [],
                "lat": 19.0,
                "lon": 72.8,
                "city": test_city,
                "state": "Maharashtra",
                "source": "CITIZEN",
            }
            res = self.client.post("/api/v1/ingest/internal", json=payload)
            self.assertEqual(res.status_code, 201)

        # Check anomalies endpoint with threshold=3
        res = self.client.get("/api/v1/analytics/anomalies?threshold=3")
        self.assertEqual(res.status_code, 200)
        anomalies = res.json()
        self.assertIsInstance(anomalies, list)
        matching = [a for a in anomalies if a["city"] == test_city and a["eventType"] == "FLOODING"]
        self.assertGreater(len(matching), 0)
        self.assertEqual(matching[0]["reportCount"], 3)
        self.assertEqual(matching[0]["severity"], "WATCH")

    def test_13_cap_alert_generation(self):
        import xml.etree.ElementTree as ET

        # 1. Test rejection of PENDING event
        list_res = self.client.get("/api/v1/events?pageSize=50")
        events = list_res.json()
        pending_event = next((e for e in events if e["verificationStatus"] == "PENDING"), None)
        if pending_event:
            res_bad = self.client.post(
                f"/api/v1/admin/events/{pending_event['id']}/generate-alert",
                headers={"X-Admin-Token": "test-secret-token"},
            )
            self.assertEqual(res_bad.status_code, 400)
            self.assertIn("VERIFIED", res_bad.json()["detail"])

        # 2. Test generation for Moderate, Severe, and Extreme severity tiers
        # Create test events directly in database to control trustScores
        from database import SessionLocal
        import crud

        db = SessionLocal()
        try:
            ev_mod = crud.create_weather_event(
                db=db,
                source="CITIZEN",
                raw_text="Moderate rainfall causing minor water accumulation",
                media_urls=[],
                lat=18.5204,
                lon=73.8567,
                city="Pune",
                state="Maharashtra",
                classification={
                    "eventType": "RAINFALL",
                    "verificationStatus": "VERIFIED",
                    "trustScore": 55.0,
                    "factorBreakdown": {"sourceTrust": 50, "corroborationBoost": 5, "crossMatchOfficial": 0, "imageCheck": 0},
                },
            )
            ev_sev = crud.create_weather_event(
                db=db,
                source="CITIZEN",
                raw_text="Severe thunderstorm knocking down branches and tree limbs",
                media_urls=[],
                lat=19.0760,
                lon=72.8777,
                city="Mumbai",
                state="Maharashtra",
                classification={
                    "eventType": "THUNDERSTORM",
                    "verificationStatus": "VERIFIED",
                    "trustScore": 78.0,
                    "factorBreakdown": {"sourceTrust": 50, "corroborationBoost": 28, "crossMatchOfficial": 0, "imageCheck": 0},
                },
            )
            ev_ext = crud.create_weather_event(
                db=db,
                source="OFFICIAL_STATION",
                raw_text="Extreme flash flood submerging low lying areas",
                media_urls=[],
                lat=15.2993,
                lon=74.1240,
                city="Goa",
                state="Goa",
                classification={
                    "eventType": "FLOODING",
                    "verificationStatus": "VERIFIED",
                    "trustScore": 95.0,
                    "factorBreakdown": {"sourceTrust": 100, "corroborationBoost": 0, "crossMatchOfficial": 0, "imageCheck": 0},
                },
            )

            # Generate alerts for all three
            res_mod = self.client.post(
                f"/api/v1/admin/events/{ev_mod.id}/generate-alert",
                headers={"X-Admin-Token": "test-secret-token"},
                json={"adminUsername": "chief_duty_officer"},
            )
            self.assertEqual(res_mod.status_code, 201)
            cap_mod = res_mod.json()
            self.assertEqual(cap_mod["severity"], "Moderate")
            self.assertIn("<alert", cap_mod["xmlPayload"])

            res_sev = self.client.post(
                f"/api/v1/admin/events/{ev_sev.id}/generate-alert",
                headers={"X-Admin-Token": "test-secret-token"},
                json={"adminUsername": "chief_duty_officer"},
            )
            self.assertEqual(res_sev.status_code, 201)
            cap_sev = res_sev.json()
            self.assertEqual(cap_sev["severity"], "Severe")

            res_ext = self.client.post(
                f"/api/v1/admin/events/{ev_ext.id}/generate-alert",
                headers={"X-Admin-Token": "test-secret-token"},
                json={"adminUsername": "chief_duty_officer"},
            )
            self.assertEqual(res_ext.status_code, 201)
            cap_ext = res_ext.json()
            self.assertEqual(cap_ext["severity"], "Extreme")
            self.assertEqual(cap_ext["certainty"], "Observed")

            # Validate output XML is well-formed using ElementTree
            parsed_xml = ET.fromstring(cap_ext["xmlPayload"])
            self.assertIn("alert", parsed_xml.tag)

            # 3. Test GET /api/v1/admin/alerts (History)
            res_history = self.client.get(
                "/api/v1/admin/alerts",
                headers={"X-Admin-Token": "test-secret-token"},
            )
            self.assertEqual(res_history.status_code, 200)
            alerts_list = res_history.json()
            self.assertGreaterEqual(len(alerts_list), 3)

            # 4. Test GET /api/v1/admin/alerts/{id}/xml download endpoint
            alert_id = cap_ext["id"]
            res_xml = self.client.get(
                f"/api/v1/admin/alerts/{alert_id}/xml",
                headers={"X-Admin-Token": "test-secret-token"},
            )
            self.assertEqual(res_xml.status_code, 200)
            self.assertIn("application/xml", res_xml.headers["content-type"])
            self.assertIn(f'attachment; filename="cap_alert_{alert_id}.xml"', res_xml.headers["content-disposition"])
            self.assertIn("<alert", res_xml.text)

        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

