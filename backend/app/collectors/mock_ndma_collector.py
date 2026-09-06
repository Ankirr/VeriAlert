import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

MOCK_NDMA_ALERTS = [
    {
        "alert_id": "SACHET-ALERT-2026-0881",
        "title": "NDMA Sachet Alert: Flash Flood Warning in Brahmaputra River Basin",
        "description": "Central Water Commission reports Brahmaputra flowing above danger mark in Dibrugarh and Guwahati. Disaster response teams deployed. Citizens in low-lying riparian areas advised to evacuate immediately to designated relief centers.",
        "severity": "Severe",
        "location": "Guwahati, Dibrugarh, Assam",
        "url": "https://sachet.ndma.gov.in/alerts/mock_sachet_0881"
    },
    {
        "alert_id": "SACHET-ALERT-2026-0882",
        "title": "NDMA Sachet Alert: Landslide Risk High along Rishikesh-Badrinath Highway",
        "description": "Due to persistent torrential downpours, slope failure and debris flow observed near Chamoli. Traffic suspended on NH-58. SDRF clearance teams on site.",
        "severity": "High",
        "location": "Chamoli, Uttarakhand",
        "url": "https://sachet.ndma.gov.in/alerts/mock_sachet_0882"
    },
    {
        "alert_id": "SACHET-ALERT-2026-0883",
        "title": "NDMA Sachet Advisory: Urban Waterlogging & Lightning Warning in Mumbai",
        "description": "Severe thunder activity accompanied by heavy showers expected in Mumbai Suburban and Thane. High tide of 4.2m expected at 14:30 hrs. Avoid venturing near seafront.",
        "severity": "Moderate",
        "location": "Mumbai, Thane, Maharashtra",
        "url": "https://sachet.ndma.gov.in/alerts/mock_sachet_0883"
    }
]

class MockNDMACollector(BaseCollector):
    """
    Mock official disaster alert collector simulating the NDMA Sachet system.
    Matches standard schema so it serves as a drop-in replacement when official API access is granted.
    Clearly labeled MOCK with source_type='official' and is_mock=True.
    Normalized into unified schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}.
    """
    def __init__(self):
        super().__init__(source_name="NDMA Sachet (MOCK)", source_type="official")

    async def fetch(self) -> List[NormalizedDisasterItem]:
        logger.info("[NDMA Sachet (MOCK)] Generating official government disaster alerts.")
        items = []
        now = datetime.now(timezone.utc)

        for idx, alert in enumerate(MOCK_NDMA_ALERTS):
            alert_time = now - timedelta(minutes=idx * 30)
            raw_text = f"{alert['title']}\n\n{alert['description']}".strip()

            item = NormalizedDisasterItem(
                id=str(uuid.uuid4()),
                source="NDMA Sachet (MOCK)",
                source_type="official",
                timestamp=alert_time,
                location_text=alert["location"],
                raw_text=raw_text,
                url=alert["url"],
                is_mock=True,
                title=alert["title"],
                raw_metadata={
                    "authority": "National Disaster Management Authority (Simulated Sachet)",
                    "alert_id": alert["alert_id"],
                    "severity": alert["severity"],
                    "is_official_mock": True
                }
            )
            items.append(item)

        return items
