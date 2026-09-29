#!/usr/bin/env python3
"""
social_simulated_feed.py - Simulated Social Media Feed Ingestion Service (PS 26069)

Implements the Mock-Mode Principle for social media feeds (source="SOCIAL_SIMULATED"):
- Class `SocialFeedClient` with `fetch_recent(hashtag: str) -> list[dict]`
- Transparently switches between X/Twitter API v2 (if TWITTER_BEARER_TOKEN is set)
  and a pre-built local dataset of ~200 realistic Indian weather posts with ~20%
  deliberately implausible/fake entries for ML verification testing.
- Replay engine with configurable emission rates (5-10s default) and demo fast-forward mode.
"""

import os
import sys
import time
import json
import random
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import requests
from common import (
    CityGeoLookup,
    post_to_backend,
    validate_raw_report,
    DEFAULT_BACKEND_URL,
    DEFAULT_INGEST_ENDPOINT,
    TWITTER_BEARER_TOKEN,
    DATA_DIR
)

logger = logging.getLogger("SocialFeedClient")

SIMULATED_DATA_FILE = os.path.join(DATA_DIR, "simulated_tweets.json")


class SocialFeedClient:
    """
    Client for fetching weather-related social media posts.

    Mock-Mode Principle:
    - If TWITTER_BEARER_TOKEN is set: queries Twitter/X v2 Search API.
    - If TWITTER_BEARER_TOKEN is absent: loads from pre-built local dataset of ~200 posts
      containing realistic Indian weather events and ~20% test anomalies.
    - Every returned dictionary is shaped strictly as RawReport matching the Shared Contract.
    """

    def __init__(self, bearer_token: Optional[str] = TWITTER_BEARER_TOKEN, data_file: str = SIMULATED_DATA_FILE):
        self.bearer_token = bearer_token
        self.data_file = data_file
        self.geo_lookup = CityGeoLookup.get_instance()
        self.is_mock_mode = not bool(self.bearer_token and self.bearer_token.strip())

        if self.is_mock_mode:
            logger.info("TWITTER_BEARER_TOKEN absent. Running SocialFeedClient in Mock Mode (Section 1 Mock-Mode Principle).")
        else:
            logger.info("TWITTER_BEARER_TOKEN present. Running SocialFeedClient in Live Twitter/X API Mode.")

    def _fetch_from_twitter_api(self, hashtag: str) -> List[Dict[str, Any]]:
        """Queries Twitter/X API v2 search endpoint."""
        url = "https://api.twitter.com/2/tweets/search/recent"
        query = hashtag if hashtag and hashtag != "all" else "India (weather OR rain OR flood OR heatwave)"
        params = {
            "query": f"{query} -is:retweet lang:en",
            "tweet.fields": "created_at,geo,author_id,attachments",
            "expansions": "attachments.media_keys",
            "media.fields": "url,preview_image_url",
            "max_results": 20
        }
        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                tweets = data.get("data", [])
                media_map = {m.get("media_key"): m.get("url") or m.get("preview_image_url") for m in data.get("includes", {}).get("media", [])}

                results = []
                for tweet in tweets:
                    text = tweet.get("text", "")
                    city, state, lat, lon = self.geo_lookup.match_location(text)
                    media_keys = tweet.get("attachments", {}).get("media_keys", [])
                    media_urls = [media_map[k] for k in media_keys if k in media_map and media_map[k]]

                    results.append({
                        "source": "SOCIAL_SIMULATED",
                        "rawText": text,
                        "mediaUrls": media_urls,
                        "reportedAt": tweet.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
                        "lat": round(lat, 4),
                        "lon": round(lon, 4),
                        "city": city,
                        "state": state,
                        "sourceMeta": {
                            "simulated": False,
                            "tweetId": tweet.get("id"),
                            "authorId": tweet.get("author_id"),
                            "hashtag": hashtag
                        }
                    })
                return results
            else:
                logger.warning(f"Twitter API returned HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error querying Twitter API: {e}")

        # If live API fails, seamlessly fallback to mock dataset
        logger.info("Falling back to local simulated feed dataset...")
        return self._fetch_from_local_file(hashtag)

    def _fetch_from_local_file(self, hashtag: str) -> List[Dict[str, Any]]:
        """Reads from local pre-built dataset of ~200 posts with refreshed timestamps."""
        if not os.path.exists(self.data_file):
            logger.error(f"Simulated posts file not found at {self.data_file}")
            return []

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                posts = data.get("posts", [])
        except Exception as e:
            logger.error(f"Error reading {self.data_file}: {e}")
            return []

        # Filter by hashtag if specified
        filtered = []
        clean_tag = hashtag.lower().replace("#", "").strip() if hashtag else ""

        now = datetime.now(timezone.utc)

        for idx, post in enumerate(posts):
            p_copy = json.loads(json.dumps(post))  # deep copy
            # Refresh reportedAt dynamically to recent times (last 0 to 180 minutes)
            minutes_offset = (idx * 3) % 180
            p_copy["reportedAt"] = (now - timedelta(minutes=minutes_offset)).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Guarantee contract fields
            p_copy["source"] = "SOCIAL_SIMULATED"
            if "sourceMeta" not in p_copy or not isinstance(p_copy["sourceMeta"], dict):
                p_copy["sourceMeta"] = {}
            p_copy["sourceMeta"]["simulated"] = True

            if not clean_tag or clean_tag == "all":
                filtered.append(p_copy)
            else:
                raw_text_lower = p_copy.get("rawText", "").lower()
                meta_tag = str(p_copy.get("sourceMeta", {}).get("hashtag", "")).lower()
                city_tag = str(p_copy.get("city", "")).lower()
                if clean_tag in raw_text_lower or clean_tag in meta_tag or clean_tag in city_tag:
                    filtered.append(p_copy)

        return filtered if filtered else posts

    def fetch_recent(self, hashtag: str = "") -> List[Dict[str, Any]]:
        """
        Public contract interface method:
        fetch_recent(hashtag: str) -> list[dict]
        Returns list of RawReport-shaped dictionaries.
        """
        if self.is_mock_mode:
            reports = self._fetch_from_local_file(hashtag)
        else:
            reports = self._fetch_from_twitter_api(hashtag)

        # Validate all reports against contract
        valid_reports = []
        for r in reports:
            errors = validate_raw_report(r)
            if errors:
                logger.error(f"Validation failure in social report: {errors}")
            else:
                valid_reports.append(r)

        return valid_reports


class SocialFeedReplayer:
    """
    Replays simulated social posts at a configurable rate,
    posting each event to the backend ingest API.
    """

    def __init__(
        self,
        client: SocialFeedClient,
        backend_url: str = DEFAULT_BACKEND_URL,
        endpoint: str = DEFAULT_INGEST_ENDPOINT,
        dry_run: bool = False,
        rate_seconds: float = 5.0,
        loop: bool = False,
        hashtag: str = "all"
    ):
        self.client = client
        self.backend_url = backend_url
        self.endpoint = endpoint
        self.dry_run = dry_run
        self.rate_seconds = rate_seconds
        self.loop = loop
        self.hashtag = hashtag

    def start_replay(self, limit: Optional[int] = None) -> int:
        """Starts streaming social reports according to pacing configuration."""
        iteration = 1
        total_posted = 0

        while True:
            logger.info(f"--- Starting Replay Round {iteration} (Filter: '{self.hashtag}') ---")
            posts = self.client.fetch_recent(self.hashtag)
            logger.info(f"Loaded {len(posts)} posts for replay.")

            if not posts:
                logger.warning("No posts available to replay.")
                break

            for idx, post in enumerate(posts, 1):
                # Dynamically set current timestamp for real-time live ingestion feel
                post["reportedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                is_anomaly = post.get("sourceMeta", {}).get("isAnomaly", False)
                tag_label = f"[ANOMALY: {post.get('sourceMeta', {}).get('anomalyType')}]" if is_anomaly else "[NORMAL]"

                logger.info(
                    f"[{idx}/{len(posts)}] Emitting {tag_label} post for {post.get('city')}, {post.get('state')}: "
                    f"\"{post.get('rawText')[:60]}...\""
                )

                post_to_backend(
                    payload=post,
                    endpoint=self.endpoint,
                    backend_url=self.backend_url,
                    dry_run=self.dry_run,
                    logger=logger
                )
                total_posted += 1

                if limit and total_posted >= limit:
                    logger.info(f"Reached limit of {limit} emitted posts.")
                    return total_posted

                # Delay before next post
                if self.rate_seconds > 0:
                    time.sleep(self.rate_seconds)

            if not self.loop:
                break

            iteration += 1
            logger.info("Looping social stream for continuous demo...")
            time.sleep(1.0)

        return total_posted


def main():
    parser = argparse.ArgumentParser(description="Simulated Social Feed Ingestion Service (PS 26069)")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted JSON to stdout instead of sending HTTP POST")
    parser.add_argument("--once", action="store_true", help="Run once without looping")
    parser.add_argument("--loop", action="store_true", help="Continuously loop through the dataset (ideal for live demo)")
    parser.add_argument("--rate", type=float, default=5.0, help="Interval in seconds between individual post emissions (default: 5.0s)")
    parser.add_argument("--fast-forward", action="store_true", help="Fast-forward mode for live demos (rate = 0.2s)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of posts to emit")
    parser.add_argument("--hashtag", type=str, default="all", help="Hashtag / keyword filter (e.g. #MumbaiRains, #DelhiWeather, all)")
    parser.add_argument("--backend-url", type=str, default=DEFAULT_BACKEND_URL, help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})")
    parser.add_argument("--endpoint", type=str, default=DEFAULT_INGEST_ENDPOINT, help=f"Backend ingest endpoint (default: {DEFAULT_INGEST_ENDPOINT})")
    parser.add_argument("--save-samples", type=str, default=None, help="Save sample JSON reports array to file")

    args = parser.parse_args()

    # Fast forward mode overrides rate
    rate = 0.2 if args.fast_forward else args.rate

    client = SocialFeedClient()

    if args.save_samples:
        posts = client.fetch_recent(args.hashtag)
        sample_limit = args.limit or 10
        samples = posts[:sample_limit]
        os.makedirs(os.path.dirname(os.path.abspath(args.save_samples)) or ".", exist_ok=True)
        with open(args.save_samples, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(samples)} sample social reports to {args.save_samples}")

        if not args.dry_run and not args.once and not args.loop:
            return

    replayer = SocialFeedReplayer(
        client=client,
        backend_url=args.backend_url,
        endpoint=args.endpoint,
        dry_run=args.dry_run,
        rate_seconds=rate,
        loop=args.loop,
        hashtag=args.hashtag
    )

    logger.info("Starting Simulated Social Media Ingestion Feed...")
    logger.info(f"Emission Rate: {rate}s/event | Fast-Forward: {args.fast_forward} | Dry-Run: {args.dry_run} | Loop: {args.loop}")

    try:
        replayer.start_replay(limit=args.limit)
    except KeyboardInterrupt:
        logger.info("Social Feed replay terminated by user.")


if __name__ == "__main__":
    main()
