"""
News Collection Module
----------------------
Yeh module various sources (RSS feeds, APIs) se news articles collect karta hai.
Production-grade features:
- Proper logging
- Retry with exponential backoff
- Regex-based text cleaning
- Type hints
- Error isolation (ek source fail ho toh baaki na ruke)
"""

import os
import re
import sys
import json
import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
import feedparser

# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/news_collection.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
USER_AGENT = "AgriLearningPoint/1.0 (+https://github.com/agrilearningpoint)"
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # exponential backoff: 2, 4, 8 seconds
DEFAULT_SOURCES_FILE = "config/news_sources.json"
OUTPUT_DIR = "data/raw"


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------
def clean_text(text: str) -> str:
    """
    Remove HTML tags, extra whitespace, and non-printable characters.
    Uses regex for robust cleaning.
    """
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Replace multiple spaces/newlines with single space
    text = re.sub(r"\s+", " ", text)
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E]", "", text)
    return text.strip()


def fetch_url(url: str) -> Optional[str]:
    """
    Fetch URL content with retries and exponential backoff.
    Returns response text or None if all retries fail.
    """
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug("Fetching URL (attempt %d/%d): %s", attempt, MAX_RETRIES, url)
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            wait = BACKOFF_FACTOR ** attempt + random.uniform(0, 1)
            logger.warning(
                "Attempt %d failed for %s: %s. Retrying in %.1f seconds...",
                attempt, url, exc, wait
            )
            time.sleep(wait)
    logger.error("All %d attempts failed for URL: %s", MAX_RETRIES, url)
    return None


def extract_articles_from_feed(feed_url: str) -> List[Dict[str, Any]]:
    """
    Parse RSS/Atom feed and return list of article dictionaries.
    """
    articles: List[Dict[str, Any]] = []
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            logger.warning("Feed parser warning for %s: %s", feed_url, feed.bozo_exception)

        for entry in feed.entries:
            article = {
                "title": clean_text(entry.get("title", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": clean_text(entry.get("summary", "")),
                "source_feed": feed_url,
                "collected_at": datetime.utcnow().isoformat(),
            }
            if article["title"] and article["link"]:
                articles.append(article)
        logger.info("Extracted %d articles from %s", len(articles), feed_url)
    except Exception as exc:
        logger.exception("Failed to parse feed %s: %s", feed_url, exc)
    return articles


def collect_news(sources: List[str]) -> List[Dict[str, Any]]:
    """
    Collect news from multiple sources. Errors in one source won't stop others.
    """
    all_articles: List[Dict[str, Any]] = []
    for source in sources:
        try:
            logger.info("Processing source: %s", source)
            articles = extract_articles_from_feed(source)
            all_articles.extend(articles)
        except Exception as exc:
            logger.exception("Error processing source %s: %s", source, exc)
    return all_articles


def save_articles(articles: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save collected articles to a JSON file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d articles to %s", len(articles), output_path)


# ------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------
def main() -> None:
    """
    Main function to orchestrate news collection.
    """
    # Load sources from config file
    sources_file = os.getenv("NEWS_SOURCES_FILE", DEFAULT_SOURCES_FILE)
    if not os.path.exists(sources_file):
        logger.error("Sources file not found: %s", sources_file)
        sys.exit(1)

    with open(sources_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    sources = config.get("rss_feeds", [])
    if not sources:
        logger.error("No RSS feeds found in %s", sources_file)
        sys.exit(1)

    logger.info("Starting news collection from %d sources", len(sources))
    articles = collect_news(sources)

    if not articles:
        logger.error("No articles collected. Exiting.")
        sys.exit(1)

    # Output file with date
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    output_file = os.path.join(OUTPUT_DIR, f"news_{date_str}.json")
    save_articles(articles, output_file)

    logger.info("News collection completed successfully.")


if __name__ == "__main__":
    main()
