import logging
import feedparser
import httpx
from datetime import datetime, timezone
from dateutil import parser as date_parser
from typing import List
from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

# Default live open RSS feeds (USGS Earthquakes & GDACS Official RSS)
DEFAULT_RSS_FEEDS = [
    {
        "name": "USGS Earthquakes RSS",
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.atom"
    },
    {
        "name": "GDACS Global Disaster RSS",
        "url": "https://www.gdacs.org/xml/rss.xml"
    }
]

class RSSFeedCollector(BaseCollector):
    def __init__(self, feeds: List[dict] = None):
        super().__init__(source_name="RSS Feed Reader", source_type="rss_feed")
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    async def fetch(self) -> List[NormalizedDisasterItem]:
        normalized_items: List[NormalizedDisasterItem] = []

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for feed_info in self.feeds:
                try:
                    logger.info(f"Fetching RSS feed from {feed_info['url']}...")
                    resp = await client.get(feed_info["url"])
                    if resp.status_code != 200:
                        logger.warning(f"Failed to fetch RSS {feed_info['url']}: HTTP {resp.status_code}")
                        continue
                    
                    parsed = feedparser.parse(resp.text)
                    for entry in parsed.entries[:10]:  # Cap to recent 10 entries per feed
                        # Extract timestamp
                        published_dt = datetime.now(timezone.utc)
                        if hasattr(entry, "published"):
                            try:
                                published_dt = date_parser.parse(entry.published)
                            except Exception:
                                pass
                        elif hasattr(entry, "updated"):
                            try:
                                published_dt = date_parser.parse(entry.updated)
                            except Exception:
                                pass

                        # Extract Geo Point if available (georss:point or point tag)
                        lat, lon = None, None
                        if hasattr(entry, "georss_point"):
                            try:
                                coords = entry.georss_point.strip().split()
                                lat, lon = float(coords[0]), float(coords[1])
                            except Exception:
                                pass
                        elif hasattr(entry, "where") and hasattr(entry.where, "coordinates"):
                            try:
                                coords = entry.where.coordinates
                                lon, lat = float(coords[0]), float(coords[1])
                            except Exception:
                                pass

                        raw_text = entry.get("summary", "") or entry.get("title", "")
                        title = entry.get("title", "Untitled Feed Item")
                        link = entry.get("link", feed_info["url"])

                        item = NormalizedDisasterItem(
                            source=feed_info["name"],
                            source_type=self.source_type,
                            timestamp=published_dt,
                            location_name=title,
                            latitude=lat,
                            longitude=lon,
                            raw_text=raw_text,
                            title=title,
                            url=link,
                            raw_metadata={"feed_url": feed_info["url"], "author": entry.get("author", "Open RSS")}
                        )
                        normalized_items.append(item)
                except Exception as e:
                    logger.error(f"Error parsing RSS feed {feed_info['url']}: {e}")

        return normalized_items
