import logging
from datetime import datetime, timezone
from typing import List
import httpx
import feedparser

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem
from app.config import settings
from app.collectors.mock_gov_alert import MOCK_GOV_ALERTS

logger = logging.getLogger(__name__)

class RealGovAlertCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="Official Government Emergency Alert Services (NWS & GDACS)", source_type="gov_alert")
        self.nws_url = settings.NWS_API_URL
        self.gdacs_url = settings.GDACS_RSS_URL

    async def fetch(self) -> List[NormalizedDisasterItem]:
        logger.info("Fetching real government emergency alerts from NWS & GDACS...")
        items: List[NormalizedDisasterItem] = []

        # 1. Fetch NWS Active Emergency Alerts (US NOAA)
        try:
            headers = {"User-Agent": "DisasterAlertFramework/1.0 (contact@example.com)"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.nws_url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    features = data.get("features", [])
                    logger.info(f"NWS Alert API returned {len(features)} active emergency alerts.")

                    for feat in features[:15]:
                        props = feat.get("properties", {})
                        geom = feat.get("geometry")

                        lat, lon = None, None
                        if geom and geom.get("type") == "Point":
                            coords = geom.get("coordinates", [])
                            if len(coords) >= 2:
                                lon, lat = coords[0], coords[1]

                        sent_str = props.get("sent") or props.get("effective")
                        ts = datetime.fromisoformat(sent_str.replace("Z", "+00:00")) if sent_str else datetime.now(timezone.utc)

                        item = NormalizedDisasterItem(
                            source=f"NWS ({props.get('senderName', 'NOAA')})",
                            source_type=self.source_type,
                            timestamp=ts,
                            location_name=props.get("areaDesc", "United States"),
                            latitude=lat,
                            longitude=lon,
                            raw_text=f"[{props.get('severity', 'Alert')}] {props.get('headline', '')} - {props.get('description', '')[:300]}",
                            title=props.get("headline") or props.get("event"),
                            url=props.get("@id") or props.get("web"),
                            raw_metadata={
                                "event": props.get("event"),
                                "severity": props.get("severity"),
                                "urgency": props.get("urgency"),
                                "certainty": props.get("certainty"),
                                "is_official": True,
                                "official_authority_score": 1.0
                            }
                        )
                        items.append(item)
        except Exception as e:
            logger.warning(f"Could not fetch NWS Government Alerts: {e}")

        # 2. Fetch GDACS (Global Disaster Alert and Coordination System) RSS
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.gdacs_url)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    logger.info(f"GDACS RSS returned {len(feed.entries)} global disaster alert entries.")
                    for entry in feed.entries[:10]:
                        lat = float(entry.geo_lat) if hasattr(entry, 'geo_lat') else None
                        lon = float(entry.geo_long) if hasattr(entry, 'geo_long') else None

                        item = NormalizedDisasterItem(
                            source="GDACS Global Alerts",
                            source_type=self.source_type,
                            timestamp=datetime.now(timezone.utc),
                            location_name=entry.get("title", "Global"),
                            latitude=lat,
                            longitude=lon,
                            raw_text=entry.get("summary", entry.get("title", "")),
                            title=entry.get("title"),
                            url=entry.get("link"),
                            raw_metadata={
                                "agency": "GDACS UN/EC",
                                "official_authority_score": 1.0,
                                "is_official": True
                            }
                        )
                        items.append(item)
        except Exception as e:
            logger.warning(f"Could not fetch GDACS alerts: {e}")

        # Fallback to mock data if no items were fetched from live APIs
        if not items:
            logger.info("No live government alerts retrieved. Utilizing fallback mock payload.")
            for alert in MOCK_GOV_ALERTS:
                dt = datetime.fromisoformat(alert["effective_time"])
                items.append(NormalizedDisasterItem(
                    source=alert["agency"],
                    source_type=self.source_type,
                    timestamp=dt,
                    location_name=alert["area_description"],
                    latitude=alert["latitude"],
                    longitude=alert["longitude"],
                    raw_text=f"[{alert['severity']}] {alert['headline']} - {alert['description']}",
                    title=alert["headline"],
                    url=alert["official_url"],
                    raw_metadata={"alert_id": alert["alert_id"], "is_official": True, "fallback": True}
                ))

        return items
