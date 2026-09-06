import logging
import uuid
import feedparser
from datetime import datetime, timezone
from typing import List
from dateutil import parser as date_parser

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

# Specific disaster keywords for regional news feeds
DOMESTIC_DISASTER_TERMS = [
    "waterlog", "water-logging", "flood", "flooding", "heavy rain",
    "red alert", "orange alert", "cloudburst", "landslide", "cyclone",
    "inundat", "submerged", "dam level", "breach", "embankment", "heatwave"
]

LOCAL_FEEDS = [
    ("NDTV Cities", "https://feeds.feedburner.com/ndtvnews-cities-news"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ("The Hindu National", "https://www.thehindu.com/news/national/feeder/default.rss"),
]

class RegionalRSSCollector(BaseCollector):
    """
    Live collector polling domestic Indian news RSS feeds (NDTV Cities, Times of India, The Hindu)
    for city-level and localized disaster reports (e.g. city waterlogging, red alerts, river floods).
    Normalized into unified schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}.
    """
    def __init__(self):
        super().__init__(source_name="Regional Indian RSS", source_type="news")

    async def fetch(self) -> List[NormalizedDisasterItem]:
        items: List[NormalizedDisasterItem] = []
        seen_urls = set()

        for feed_name, feed_url in LOCAL_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    title = (getattr(entry, "title", "") or "").strip()
                    summary = (getattr(entry, "summary", "") or "").strip()
                    url = getattr(entry, "link", None)

                    if not url or url in seen_urls or not title:
                        continue

                    combined = f"{title} {summary}".lower()
                    
                    # Match domestic disaster terms
                    matched_term = None
                    for term in DOMESTIC_DISASTER_TERMS:
                        if term in combined:
                            matched_term = term
                            break

                    if not matched_term:
                        continue

                    seen_urls.add(url)

                    # Extract city/region from title or summary
                    location_hint = None
                    for city in ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata", "Assam", "Kerala", "Bihar", "Nepal", "Shimla", "Pune"]:
                        if city.lower() in combined:
                            location_hint = city
                            break

                    # Parse timestamp
                    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
                    try:
                        dt = date_parser.parse(published) if published else datetime.now(timezone.utc)
                    except Exception:
                        dt = datetime.now(timezone.utc)

                    raw_text = f"{title}\n\n{summary}".strip()

                    item = NormalizedDisasterItem(
                        id=str(uuid.uuid4()),
                        source=f"{feed_name} RSS",
                        source_type="news",
                        timestamp=dt,
                        location_text=location_hint or "India (Regional)",
                        raw_text=raw_text,
                        url=url,
                        is_mock=False,
                        title=title,
                        raw_metadata={
                            "matched_term": matched_term,
                            "feed_name": feed_name,
                            "scope": "Domestic Regional Feed"
                        }
                    )
                    items.append(item)

            except Exception as e:
                logger.warning(f"[RegionalRSS] Could not parse feed '{feed_name}': {e}")
                continue

        logger.info(f"[RegionalRSS] Collected {len(items)} live domestic disaster items from Indian news feeds.")
        return items
