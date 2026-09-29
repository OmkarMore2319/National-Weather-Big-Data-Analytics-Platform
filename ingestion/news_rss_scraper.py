#!/usr/bin/env python3
"""
news_rss_scraper.py - RSS Feed Ingestion Service for Weather Platform (PS 26069)

Ingests real-time Indian weather and news headlines from free RSS feeds,
extracts geographic locations using a static Indian cities lookup table (~300 cities),
formats payloads according to the RawReport schema (source="NEWS_RSS"),
and POSTs them to the backend ingest endpoint (POST /api/v1/ingest/internal).

Includes:
- Robust error handling, retry + backoff (never crashes on feed or backend failures)
- Standalone --dry-run mode for offline testing
- Built-in Mock-Mode fallback cache if external feeds are unreachable
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from email.utils import parsedate_to_datetime

import feedparser
from common import (
    CityGeoLookup,
    post_to_backend,
    validate_raw_report,
    DEFAULT_BACKEND_URL,
    DEFAULT_INGEST_ENDPOINT,
    DATA_DIR
)

logger = logging.getLogger("NewsRssScraper")

# Free Indian weather and national news RSS feeds
DEFAULT_RSS_FEEDS = [
    {
        "name": "Google News (India Weather Search)",
        "url": "https://news.google.com/rss/search?q=India+weather+OR+rain+OR+flood+OR+heatwave+OR+monsoon+OR+cyclone&hl=en-IN&gl=IN&ceid=IN:en"
    },
    {
        "name": "The Hindu (National Feed)",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss"
    },
    {
        "name": "The Indian Express (India Feed)",
        "url": "https://indianexpress.com/section/india/feed/"
    }
]

FALLBACK_FILE = os.path.join(DATA_DIR, "fallback_rss_feeds.json")


class NewsRssScraper:
    """
    Scrapes and parses RSS feeds, geocodes weather reports,
    and publishes them to the backend API.
    """

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        endpoint: str = DEFAULT_INGEST_ENDPOINT,
        dry_run: bool = False,
        feeds: Optional[List[Dict[str, str]]] = None,
        max_retries: int = 3
    ):
        self.backend_url = backend_url
        self.endpoint = endpoint
        self.dry_run = dry_run
        self.feeds = feeds or DEFAULT_RSS_FEEDS
        self.max_retries = max_retries
        self.geo_lookup = CityGeoLookup.get_instance()
        self.seen_guids: Set[str] = set()

    def _parse_published_date(self, entry: Any) -> str:
        """Parses entry publication timestamp into standard ISO 8601 UTC string."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        if hasattr(entry, "published") and entry.published:
            try:
                dt = parsedate_to_datetime(entry.published)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        # Default to current UTC time
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _extract_media_urls(self, entry: Any) -> List[str]:
        """Extracts media/enclosure URLs from RSS entry."""
        media_urls = []

        # Check enclosures
        if hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                href = enc.get("href") or enc.get("url")
                if href and href.startswith("http"):
                    media_urls.append(href)

        # Check media_content
        if hasattr(entry, "media_content") and entry.media_content:
            for media in entry.media_content:
                url = media.get("url")
                if url and url.startswith("http"):
                    media_urls.append(url)

        # Check media_thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            for thumb in entry.media_thumbnail:
                url = thumb.get("url")
                if url and url.startswith("http"):
                    media_urls.append(url)

        return list(dict.fromkeys(media_urls))  # remove duplicates

    def _clean_text(self, text: str) -> str:
        """Removes HTML tags and normalizes whitespace."""
        if not text:
            return ""
        import re
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"&nbsp;|&amp;|&quot;|&#39;|&lt;|&gt;", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _fetch_feed_with_retry(self, feed_url: str) -> Optional[Any]:
        """Fetches and parses an RSS feed with retry logic and error suppression."""
        for attempt in range(1, self.max_retries + 1):
            try:
                feed = feedparser.parse(feed_url)
                if feed.bozo and not feed.entries:
                    logger.warning(f"Feed parser warning for {feed_url}: {feed.bozo_exception}")
                    if attempt < self.max_retries:
                        time.sleep(1.0 * attempt)
                        continue
                return feed
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed fetching {feed_url}: {e}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)
        return None

    def _load_fallback_feed(self) -> List[Dict[str, Any]]:
        """Loads pre-built offline fallback RSS data (Mock-Mode Principle)."""
        if os.path.exists(FALLBACK_FILE):
            try:
                with open(FALLBACK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = []
                    for feed in data.get("feeds", []):
                        feed_title = feed.get("feedTitle", "Offline Fallback Weather News")
                        for itm in feed.get("items", []):
                            itm["feedTitle"] = feed_title
                            items.append(itm)
                    return items
            except Exception as e:
                logger.error(f"Error loading fallback RSS cache: {e}")
        return []

    def fetch_and_process(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Pulls from configured RSS feeds, formats into RawReport JSON,
        and returns the list of newly processed events.
        """
        processed_reports: List[Dict[str, Any]] = []
        feed_success_count = 0

        for feed_config in self.feeds:
            feed_name = feed_config["name"]
            feed_url = feed_config["url"]
            logger.info(f"Scanning RSS feed: {feed_name} ({feed_url})")

            feed = self._fetch_feed_with_retry(feed_url)
            if feed and feed.entries:
                feed_success_count += 1
                for entry in feed.entries:
                    guid = getattr(entry, "id", None) or getattr(entry, "link", None) or getattr(entry, "title", "")
                    if guid in self.seen_guids:
                        continue

                    title = self._clean_text(getattr(entry, "title", ""))
                    summary = self._clean_text(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                    combined_text = f"{title}. {summary}".strip()

                    if not combined_text:
                        continue

                    city, state, lat, lon = self.geo_lookup.match_location(combined_text)
                    reported_at = self._parse_published_date(entry)
                    media_urls = self._extract_media_urls(entry)
                    link = getattr(entry, "link", "")

                    report = {
                        "source": "NEWS_RSS",
                        "rawText": combined_text,
                        "mediaUrls": media_urls,
                        "reportedAt": reported_at,
                        "lat": round(lat, 4),
                        "lon": round(lon, 4),
                        "city": city,
                        "state": state,
                        "sourceMeta": {
                            "feedTitle": feed_name,
                            "link": link,
                            "guid": guid,
                            "published": getattr(entry, "published", "")
                        }
                    }

                    # Validate against contract schema
                    errors = validate_raw_report(report)
                    if errors:
                        logger.error(f"Validation error in RSS report: {errors}")
                        continue

                    self.seen_guids.add(guid)
                    processed_reports.append(report)

                    if limit and len(processed_reports) >= limit:
                        break

            if limit and len(processed_reports) >= limit:
                break

        # If all live feeds failed or returned zero items (e.g. offline environment),
        # use the pre-built fallback cache
        if feed_success_count == 0 or len(processed_reports) == 0:
            logger.info("Using offline fallback RSS dataset (Mock-Mode Principle)...")
            fallback_items = self._load_fallback_feed()
            for itm in fallback_items:
                guid = itm.get("link", "") or itm.get("title", "")
                if guid in self.seen_guids:
                    continue

                combined_text = f"{itm.get('title', '')}. {itm.get('summary', '')}".strip()
                city, state, lat, lon = self.geo_lookup.match_location(combined_text)

                report = {
                    "source": "NEWS_RSS",
                    "rawText": combined_text,
                    "mediaUrls": itm.get("media", []),
                    "reportedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "city": city,
                    "state": state,
                    "sourceMeta": {
                        "feedTitle": itm.get("feedTitle", "Mock Weather RSS Feed"),
                        "link": itm.get("link", ""),
                        "guid": guid,
                        "published": itm.get("published", ""),
                        "simulated": True
                    }
                }
                errors = validate_raw_report(report)
                if not errors:
                    self.seen_guids.add(guid)
                    processed_reports.append(report)

                if limit and len(processed_reports) >= limit:
                    break

        return processed_reports

    def run_cycle(self, limit: Optional[int] = None) -> int:
        """Executes a single fetch-and-post cycle."""
        reports = self.fetch_and_process(limit=limit)
        logger.info(f"Parsed {len(reports)} new weather reports from RSS feeds.")

        success_count = 0
        for report in reports:
            ok = post_to_backend(
                payload=report,
                endpoint=self.endpoint,
                backend_url=self.backend_url,
                dry_run=self.dry_run,
                logger=logger
            )
            if ok:
                success_count += 1
            # Slight pacing between individual POSTs
            time.sleep(0.05)

        return success_count


def main():
    parser = argparse.ArgumentParser(description="News/RSS Scraper for Weather Big Data Analytics Platform (PS 26069)")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted JSON to stdout instead of sending HTTP POST")
    parser.add_argument("--once", action="store_true", help="Run a single fetch pass and exit")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("RSS_POLL_INTERVAL", "45")), help="Interval in seconds between RSS scraping cycles (default: 45s)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of articles to process per cycle")
    parser.add_argument("--backend-url", type=str, default=DEFAULT_BACKEND_URL, help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})")
    parser.add_argument("--endpoint", type=str, default=DEFAULT_INGEST_ENDPOINT, help=f"Ingest endpoint (default: {DEFAULT_INGEST_ENDPOINT})")
    parser.add_argument("--save-samples", type=str, default=None, help="Save parsed JSON reports to a specified file")

    args = parser.parse_args()

    scraper = NewsRssScraper(
        backend_url=args.backend_url,
        endpoint=args.endpoint,
        dry_run=args.dry_run
    )

    logger.info("Starting News/RSS Weather Ingestion Service...")
    logger.info(f"Target Backend URL: {args.backend_url} | Endpoint: {args.endpoint} | Dry-Run: {args.dry_run}")

    if args.once or args.save_samples:
        reports = scraper.fetch_and_process(limit=args.limit)
        logger.info(f"Fetched {len(reports)} reports in single pass.")
        if args.save_samples:
            os.makedirs(os.path.dirname(os.path.abspath(args.save_samples)) or ".", exist_ok=True)
            with open(args.save_samples, "w", encoding="utf-8") as f:
                json.dump(reports, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(reports)} sample reports to {args.save_samples}")

        for r in reports:
            post_to_backend(r, endpoint=args.endpoint, backend_url=args.backend_url, dry_run=args.dry_run, logger=logger)
        return

    # Continuous polling loop (every 30-60s)
    try:
        while True:
            scraper.run_cycle(limit=args.limit)
            logger.info(f"Cycle completed. Sleeping for {args.interval} seconds before next RSS scan...")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("RSS Scraper terminated by user.")


if __name__ == "__main__":
    main()
