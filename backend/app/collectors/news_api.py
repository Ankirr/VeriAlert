import logging
import uuid
import httpx
from datetime import datetime, timezone
from typing import List, Set
from dateutil import parser as date_parser

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem
from app.config import settings

logger = logging.getLogger(__name__)

# Strict disaster keywords
VALID_DISASTER_KEYWORDS = [
    "flood", "flooding", "cloudburst", "flash flood", "inundat", "waterlog",
    "landslide", "mudslide", "rockslide", "debris flow",
    "cyclone", "depression", "heavy rain", "torrential", "monsoon", "submerged",
    "earthquake", "tremor", "aftershock", "tsunami", "heatwave", "danger mark"
]

# Granular Indian cities, districts, states & regional neighbors
REGION_KEYWORDS = {
    # Urban Municipalities & Cities
    "mumbai": "Mumbai, Maharashtra",
    "delhi": "Delhi NCR",
    "bengaluru": "Bengaluru, Karnataka",
    "bangalore": "Bengaluru, Karnataka",
    "chennai": "Chennai, Tamil Nadu",
    "kolkata": "Kolkata, West Bengal",
    "pune": "Pune, Maharashtra",
    "hyderabad": "Hyderabad, Telangana",
    "ahmedabad": "Ahmedabad, Gujarat",
    "gurugram": "Gurugram, Haryana",
    "noida": "Noida, Uttar Pradesh",
    "patna": "Patna, Bihar",
    "guwahati": "Guwahati, Assam",
    "kochi": "Kochi, Kerala",
    "shimla": "Shimla, Himachal Pradesh",
    "mandi": "Mandi, Himachal Pradesh",
    "kullu": "Kullu, Himachal Pradesh",
    "dharamshala": "Dharamshala, Himachal Pradesh",
    "chamoli": "Chamoli, Uttarakhand",
    "rudraprayag": "Rudraprayag, Uttarakhand",
    "joshimath": "Joshimath, Uttarakhand",
    "uttarkashi": "Uttarkashi, Uttarakhand",
    "wayanad": "Wayanad, Kerala",
    "idukki": "Idukki, Kerala",
    "munnar": "Munnar, Kerala",
    "dibrugarh": "Dibrugarh, Assam",
    "majuli": "Majuli, Assam",
    "saran": "Saran, Bihar",
    "cuttack": "Cuttack, Odisha",
    "puri": "Puri, Odisha",
    # States & Rivers
    "assam": "Assam",
    "bihar": "Bihar",
    "kerala": "Kerala",
    "himachal": "Himachal Pradesh",
    "uttarakhand": "Uttarakhand",
    "odisha": "Odisha",
    "gujarat": "Gujarat",
    "sikkim": "Sikkim",
    "brahmaputra": "Brahmaputra Basin, Assam",
    "ganga": "Ganga Basin, India",
    "yamuna": "Yamuna Floodplains, Delhi",
    "kosi": "Kosi River Basin, Bihar",
    "bay of bengal": "Bay of Bengal",
    "arabian sea": "Arabian Sea",
    # Regional Neighbors Affecting India
    "nepal": "Nepal",
    "bhotekoshi": "Bhotekoshi, Nepal",
    "tibet": "Tibet Border Region",
    "bangladesh": "Bangladesh",
    "sri lanka": "Sri Lanka",
    "bhutan": "Bhutan",
}

# Strict negative keywords to eliminate metaphors and irrelevant noise
EXCLUDED_METAPHORS = [
    "election", "poll", "vote", "landslide victory", "landslide win",
    "landslide majority", "afd", "republican", "democrat", "bjp", "congress",
    "movie", "film", "trailer", "box office", "album", "song", "music", "actor",
    "cricket", "football", "match", "tournament", "ipl", "trophy", "bier",
    "stock market", "shares", "wall street", "sensex", "nifty", "nasdaq"
]

class NewsAPICollector(BaseCollector):
    """
    Real-time news collector filtered for both domestic regional disasters (city/district waterlogging,
    flash floods, hill state landslides) and regional calamities affecting India.
    Normalized into unified schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}.
    """
    def __init__(self):
        super().__init__(source_name="NewsAPI", source_type="news")
        self.api_url = "https://newsapi.org/v2/everything"
        # Targeted domestic regional & district queries
        self.queries = [
            # 1. Urban domestic waterlogging & local city floods
            '(waterlogging OR "waterlogged" OR inundation OR "submerged roads") AND (Delhi OR Mumbai OR Bengaluru OR Chennai OR Kolkata OR Pune OR Gurugram)',
            # 2. Hill state / District-level landslides & flash floods
            '(landslide OR cloudburst OR "flash flood" OR "debris flow") AND (Wayanad OR Shimla OR Mandi OR Kullu OR Chamoli OR Joshimath OR Idukki OR Munnar OR Uttarakhand)',
            # 3. Rural river basins & village flooding in India & Nepal
            '(flood OR flooding OR "water level" OR breach OR "danger mark") AND (Assam OR Bihar OR Ganga OR Yamuna OR Brahmaputra OR Kosi OR Nepal OR Bhotekoshi)',
            # 4. Coastal weather alerts & cyclonic storms
            '(cyclone OR "deep depression" OR "heavy rain alert") AND (Odisha OR Gujarat OR "Bay of Bengal" OR Andhra OR Kerala OR Maharashtra)'
        ]

    async def fetch(self) -> List[NormalizedDisasterItem]:
        if not settings.NEWSAPI_KEY or settings.NEWSAPI_KEY == "your_newsapi_key_here":
            logger.warning("[NewsAPI] No valid NEWSAPI_KEY configured in .env.")
            return []

        seen_urls: Set[str] = set()
        normalized_items: List[NormalizedDisasterItem] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in self.queries:
                params = {
                    "q": query,
                    "sortBy": "publishedAt",
                    "pageSize": 20,
                    "language": "en",
                    "apiKey": settings.NEWSAPI_KEY
                }

                try:
                    response = await client.get(self.api_url, params=params)
                    if response.status_code == 429:
                        logger.warning("[NewsAPI] Rate limit reached. Continuing with collected items.")
                        break
                    elif response.status_code != 200:
                        logger.warning(f"[NewsAPI] Query returned HTTP {response.status_code}. Skipping query.")
                        continue

                    data = response.json()
                    articles = data.get("articles", [])

                    for art in articles:
                        url = art.get("url")
                        title = (art.get("title") or "").strip()
                        description = (art.get("description") or "").strip()
                        content = (art.get("content") or "").strip()

                        if not url or not title or url in seen_urls or title == "[Removed]":
                            continue

                        combined_text = f"{title} {description} {content}".lower()

                        # 1. Filter out metaphors and noise
                        if any(neg in combined_text for neg in EXCLUDED_METAPHORS):
                            continue

                        # 2. Must contain an actual disaster term
                        if not any(kw in combined_text for kw in VALID_DISASTER_KEYWORDS):
                            continue

                        # 3. Match granular location (city, district, village, or state)
                        matched_places = []
                        for key, canonical in REGION_KEYWORDS.items():
                            if key in combined_text:
                                matched_places.append(canonical)

                        if not matched_places:
                            continue

                        seen_urls.add(url)

                        # Parse timestamp
                        published_at_str = art.get("publishedAt")
                        try:
                            dt = date_parser.isoparse(published_at_str) if published_at_str else datetime.now(timezone.utc)
                        except Exception:
                            dt = datetime.now(timezone.utc)

                        source_name = art.get("source", {}).get("name") or "News Source"
                        raw_text = f"{title}\n\n{description}\n\n{content}".strip()
                        
                        # Prioritize most specific location hint (e.g. "Delhi NCR", "Wayanad, Kerala")
                        location_text = matched_places[0] if matched_places else None

                        item = NormalizedDisasterItem(
                            id=str(uuid.uuid4()),
                            source=f"NewsAPI ({source_name})",
                            source_type="news",
                            timestamp=dt,
                            location_text=location_text,
                            raw_text=raw_text,
                            url=url,
                            is_mock=False,
                            title=title,
                            raw_metadata={
                                "author": art.get("author"),
                                "source_name": source_name,
                                "matched_locations": matched_places,
                                "scope": "Domestic Regional / Calamity"
                            }
                        )
                        normalized_items.append(item)

                except Exception as ex:
                    logger.warning(f"[NewsAPI] Error executing query '{query[:30]}...': {ex}")
                    continue

        logger.info(f"[NewsAPI] Collected {len(normalized_items)} domestic regional disaster articles.")
        return normalized_items
