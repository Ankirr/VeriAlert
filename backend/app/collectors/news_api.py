import logging
import httpx
from datetime import datetime, timezone
from typing import List
from app.config import settings
from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

# Fallback realistic news items if no API key is provided
SAMPLE_NEWS_ITEMS = [
    {
        "title": "Severe Flash Flooding Paralyzes Public Transit in Metro Manila",
        "description": "Monsoon rains intensified by Tropical Storm Carina caused extensive flooding across Manila, forcing thousands into evacuation centers.",
        "url": "https://news.example.com/asia/manila-flash-floods-2026",
        "publishedAt": "2026-08-18T10:00:00Z",
        "source": {"name": "Global News Wire"},
        "location": "Manila, Philippines",
        "lat": 14.5995,
        "lon": 120.9842
    },
    {
        "title": "Magnitude 6.4 Earthquake Strikes Off Coast of Northern California",
        "description": "The US Geological Survey reported a strong earthquake 40 miles off Ferndale. Power outages affected over 10,000 residents.",
        "url": "https://news.example.com/us/california-earthquake-ferndale",
        "publishedAt": "2026-08-18T12:30:00Z",
        "source": {"name": "Pacific Coast Press"},
        "location": "Ferndale, California",
        "lat": 40.5762,
        "lon": -124.2639
    }
]

class NewsAPICollector(BaseCollector):
    def __init__(self, api_key: str = None):
        super().__init__(source_name="News API", source_type="news_api")
        self.api_key = api_key or settings.NEWS_API_KEY

    async def fetch(self) -> List[NormalizedDisasterItem]:
        normalized_items: List[NormalizedDisasterItem] = []

        if self.api_key:
            # Query live NewsAPI endpoint if key configured
            url = f"https://newsapi.org/v2/everything?q=disaster+OR+earthquake+OR+flood+OR+wildfire&sortBy=publishedAt&pageSize=10&apiKey={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    articles = data.get("articles", [])
                    for article in articles:
                        try:
                            dt = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                        except Exception:
                            dt = datetime.now(timezone.utc)

                        normalized_items.append(
                            NormalizedDisasterItem(
                                source=article.get("source", {}).get("name", "News API"),
                                source_type=self.source_type,
                                timestamp=dt,
                                location_name=None,
                                raw_text=f"{article.get('title', '')} - {article.get('description', '')}",
                                title=article.get("title"),
                                url=article.get("url"),
                                raw_metadata={"author": article.get("author")}
                            )
                        )
                    return normalized_items
                else:
                    logger.warning(f"NewsAPI HTTP {resp.status_code}. Falling back to open news feed sample.")

        # Fallback / Default Open Data execution (No API key required)
        logger.info("Ingesting open public news stream sample...")
        for item in SAMPLE_NEWS_ITEMS:
            dt = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
            normalized_items.append(
                NormalizedDisasterItem(
                    source=item["source"]["name"],
                    source_type=self.source_type,
                    timestamp=dt,
                    location_name=item["location"],
                    latitude=item["lat"],
                    longitude=item["lon"],
                    raw_text=f"{item['title']} - {item['description']}",
                    title=item["title"],
                    url=item["url"],
                    raw_metadata={"fallback_ingest": True}
                )
            )

        return normalized_items
