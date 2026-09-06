import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

MOCK_IMD_BULLETINS = [
    {
        "title": "IMD Bulletin: Depression over Bay of Bengal likely to intensify into Cyclonic Storm",
        "description": "Special Tropical Weather Outlook: Deep depression centered over Westcentral Bay of Bengal near lat 16.5N, long 86.0E. Likely to cross Andhra Pradesh and Odisha coast with wind speed 70-80 kmph gusting to 90 kmph.",
        "location": "Bay of Bengal, Odisha, Andhra Pradesh",
        "url": "https://mausam.imd.gov.in/mock_bulletin_cyclone_01",
        "category": "Cyclone"
    },
    {
        "title": "IMD Red Alert: Extremely heavy rainfall predicted across Coastal Karnataka and Goa",
        "description": "Synoptic conditions indicate intense monsoon surge. Inundation of low lying areas and disruption of rail/road traffic expected in Mangaluru, Udupi, and North Goa.",
        "location": "Coastal Karnataka, Mangaluru, Goa",
        "url": "https://mausam.imd.gov.in/mock_bulletin_rain_02",
        "category": "Heavy Rainfall"
    },
    {
        "title": "IMD Severe Weather Warning: Severe Heatwave conditions in Western Rajasthan",
        "description": "Maximum temperatures forecasted between 46°C to 48°C in Jaisalmer, Bikaner, and Barmer districts. Public advised to avoid direct sun exposure during peak afternoon hours.",
        "location": "Jaisalmer, Bikaner, Rajasthan",
        "url": "https://mausam.imd.gov.in/mock_bulletin_heatwave_03",
        "category": "Heatwave"
    }
]

class MockRSSCollector(BaseCollector):
    """
    Mock RSS bulletin collector simulating official IMD (India Meteorological Department) weather alerts.
    Clearly labeled MOCK in source name and metadata with is_mock=True.
    Normalized into unified schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}.
    """
    def __init__(self):
        super().__init__(source_name="IMD RSS (MOCK)", source_type="rss")

    async def fetch(self) -> List[NormalizedDisasterItem]:
        logger.info("[IMD RSS (MOCK)] Generating official meteorological bulletins.")
        items = []
        now = datetime.now(timezone.utc)

        for idx, bulletin in enumerate(MOCK_IMD_BULLETINS):
            # Timestamp spaced 15 minutes apart
            bulletin_time = now - timedelta(minutes=idx * 20)
            raw_text = f"{bulletin['title']}\n\n{bulletin['description']}".strip()

            item = NormalizedDisasterItem(
                id=str(uuid.uuid4()),
                source="IMD RSS (MOCK)",
                source_type="rss",
                timestamp=bulletin_time,
                location_text=bulletin["location"],
                raw_text=raw_text,
                url=bulletin["url"],
                is_mock=True,
                title=bulletin["title"],
                raw_metadata={
                    "authority": "India Meteorological Department (Simulated)",
                    "category": bulletin["category"],
                    "is_official_mock": True
                }
            )
            items.append(item)

        return items
