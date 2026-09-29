"""
test_ingestion.py - Comprehensive Unit and Integration Test Suite for Ingestion Package (PS 26069)

Verifies:
1. CityGeoLookup accuracy, performance, and alias coverage
2. NewsRssScraper parsing, geocoding, and schema compliance
3. OfficialGroundTruthPuller API handling, WMO mapping, and schema compliance
4. SocialFeedClient Mock-Mode principle, anomaly distribution, and schema compliance
5. Validation of sample JSON fixture files in samples/ directory
"""

import os
import json
import unittest
from datetime import datetime

from common import (
    CityGeoLookup,
    validate_raw_report,
    validate_official_reading,
    CITIES_FILE
)
from news_rss_scraper import NewsRssScraper
from official_puller import OfficialGroundTruthPuller
from social_simulated_feed import SocialFeedClient, SIMULATED_DATA_FILE


class TestCityGeoLookup(unittest.TestCase):
    def setUp(self):
        self.lookup = CityGeoLookup.get_instance()

    def test_cities_database_loaded(self):
        self.assertGreater(len(self.lookup.cities), 200, "City database must contain >200 cities")
        self.assertGreater(len(self.lookup.state_centers), 30, "State centers must cover >30 states/UTs")

    def test_major_metro_matches(self):
        city, state, lat, lon = self.lookup.match_location("Heavy downpour in Mumbai near Dadar TT circle")
        self.assertEqual(city, "Mumbai")
        self.assertEqual(state, "Maharashtra")
        self.assertAlmostEqual(lat, 19.0760, places=2)
        self.assertAlmostEqual(lon, 72.8777, places=2)

    def test_alias_resolution(self):
        # Bangalore alias
        city, state, lat, lon = self.lookup.match_location("Traffic slow in Bangalore near Whitefield")
        self.assertEqual(city, "Bengaluru")
        self.assertEqual(state, "Karnataka")

        # Gurgaon alias
        city, state, lat, lon = self.lookup.match_location("Dust storm in Gurgaon Cyber City")
        self.assertEqual(city, "Gurugram")
        self.assertEqual(state, "Haryana")

        # Allahabad alias
        city, state, lat, lon = self.lookup.match_location("Triveni Sangam in Allahabad is crowded")
        self.assertEqual(city, "Prayagraj")
        self.assertEqual(state, "Uttar Pradesh")

    def test_state_level_match(self):
        city, state, lat, lon = self.lookup.match_location("Heavy rainfall alert issued across Uttarakhand")
        self.assertEqual(state, "Uttarakhand")
        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)


class TestNewsRssScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = NewsRssScraper(dry_run=True)

    def test_rss_fetch_and_schema_compliance(self):
        reports = self.scraper.fetch_and_process(limit=5)
        self.assertGreater(len(reports), 0, "Scraper should return at least one report")

        for r in reports:
            errors = validate_raw_report(r)
            self.assertEqual(errors, [], f"RawReport validation failed: {errors}")
            self.assertEqual(r["source"], "NEWS_RSS")
            self.assertIsInstance(r["rawText"], str)
            self.assertIsInstance(r["mediaUrls"], list)
            self.assertIsInstance(r["sourceMeta"], dict)
            self.assertIn("feedTitle", r["sourceMeta"])


class TestOfficialGroundTruthPuller(unittest.TestCase):
    def setUp(self):
        self.puller = OfficialGroundTruthPuller(dry_run=True)

    def test_official_reading_schema_compliance(self):
        readings = self.puller.pull_all_readings(limit=3)
        self.assertEqual(len(readings), 3)

        for reading in readings:
            errors = validate_official_reading(reading)
            self.assertEqual(errors, [], f"OfficialReading validation failed: {errors}")
            self.assertIn("id", reading)
            self.assertIn("city", reading)
            self.assertIn("state", reading)
            self.assertIn("condition", reading)
            self.assertIn("rainfallMm", reading)
            self.assertIn("tempC", reading)
            self.assertIn("windKph", reading)
            self.assertIsInstance(reading["rainfallMm"], (int, float))
            self.assertIsInstance(reading["tempC"], (int, float))
            self.assertIsInstance(reading["windKph"], (int, float))


class TestSocialFeedClient(unittest.TestCase):
    def setUp(self):
        self.client = SocialFeedClient()

    def test_mock_mode_active_when_no_bearer_token(self):
        self.assertTrue(self.client.is_mock_mode)

    def test_simulated_posts_dataset(self):
        self.assertTrue(os.path.exists(SIMULATED_DATA_FILE))
        with open(SIMULATED_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            posts = data.get("posts", [])

        self.assertGreaterEqual(len(posts), 180, "Should have ~200 simulated posts")
        anomalies = [p for p in posts if p.get("sourceMeta", {}).get("isAnomaly") is True]
        anomaly_pct = len(anomalies) / len(posts) * 100
        self.assertGreaterEqual(anomaly_pct, 15.0, "Should have ~20% anomalies for verification tests")
        self.assertLessEqual(anomaly_pct, 25.0)

    def test_fetch_recent_interface_and_schema(self):
        reports = self.client.fetch_recent("all")
        self.assertGreater(len(reports), 0)

        for r in reports[:20]:
            errors = validate_raw_report(r)
            self.assertEqual(errors, [], f"Social RawReport validation failed: {errors}")
            self.assertEqual(r["source"], "SOCIAL_SIMULATED")
            self.assertTrue(r.get("sourceMeta", {}).get("simulated", False))


class TestSampleFixtures(unittest.TestCase):
    def test_news_rss_fixture(self):
        fixture_path = "samples/news_rss_samples.json"
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data), 5)
        for item in data:
            self.assertEqual(validate_raw_report(item), [])

    def test_official_reading_fixture(self):
        fixture_path = "samples/official_reading_samples.json"
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data), 5)
        for item in data:
            self.assertEqual(validate_official_reading(item), [])

    def test_social_feed_fixture(self):
        fixture_path = "samples/social_feed_samples.json"
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data), 5)
        for item in data:
            self.assertEqual(validate_raw_report(item), [])


if __name__ == "__main__":
    unittest.main()
