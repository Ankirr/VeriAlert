import logging
from datetime import datetime, timezone, timedelta
from typing import List
from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

MOCK_GOV_ALERTS = [
    {
        "alert_id": "GOV-FEMA-2026-0891",
        "agency": "FEMA National Watch Center",
        "hazard_type": "Wildfire",
        "severity": "Emergency",
        "headline": "MANDATORY EVACUATION: Rapidly spreading wildfire in Boulder County, Colorado",
        "description": "FEMA emergency declaration #4921 issued for Boulder County due to uncontained 5,000-acre wildfire driven by 50mph winds. Evacuation orders in effect for Zones 3 and 4.",
        "area_description": "Boulder County, Colorado",
        "latitude": 40.0150,
        "longitude": -105.2705,
        "effective_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "official_url": "https://www.fema.gov/disaster/alerts/4921"
    },
    {
        "alert_id": "GOV-GDACS-2026-TC04",
        "agency": "GDACS Disaster Alert Center",
        "hazard_type": "Tropical Cyclone",
        "severity": "Red Alert",
        "headline": "RED ALERT: Category 4 Tropical Cyclone Approaching Coast of Queensland",
        "description": "GDACS Red Alert issued for Tropical Cyclone Jasper. Estimated wind gusts up to 220 km/h and storm surge of 3.5 meters expected near Cairns.",
        "area_description": "Cairns, Queensland, Australia",
        "latitude": -16.9186,
        "longitude": 145.7781,
        "effective_time": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "official_url": "https://www.gdacs.org/report.aspx?eventid=109283"
    }
]

class MockGovAlertCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="Mock Government Disaster Alert API", source_type="gov_alert")

    async def fetch(self) -> List[NormalizedDisasterItem]:
        logger.info("Fetching mock government disaster alert payload...")
        items: List[NormalizedDisasterItem] = []
        
        for alert in MOCK_GOV_ALERTS:
            dt = datetime.fromisoformat(alert["effective_time"])
            item = NormalizedDisasterItem(
                source=alert["agency"],
                source_type=self.source_type,
                timestamp=dt,
                location_name=alert["area_description"],
                latitude=alert["latitude"],
                longitude=alert["longitude"],
                raw_text=f"[{alert['severity']}] {alert['headline']} - {alert['description']}",
                title=alert["headline"],
                url=alert["official_url"],
                raw_metadata={
                    "alert_id": alert["alert_id"],
                    "agency": alert["agency"],
                    "hazard_type": alert["hazard_type"],
                    "official_authority_score": 1.0,
                    "is_official": True
                }
            )
            items.append(item)
            
        return items
