import logging
import uuid
import httpx
from datetime import datetime, timezone
from typing import List
from dateutil import parser as date_parser

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

class GDELTCollector(BaseCollector):
    """
    100% Free global disaster news collector using the GDELT 2.0 Doc API (no API key required).
    Functions as primary/supplementary source for news alongside NewsAPI.
    Normalized into unified schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}.
    """
    def __init__(self):
        super().__init__(source_name="GDELT", source_type="news")
        self.api_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.query = "(flood OR earthquake OR cyclone OR hurricane OR wildfire OR landslide)"

    async def fetch(self) -> List[NormalizedDisasterItem]:
        params = {
            "query": self.query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": 20,
            "sort": "DateDesc"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        try:
            # Set a 7-second timeout for GDELT to prevent blocking the pipeline if GDELT is unresponsive
            async with httpx.AsyncClient(timeout=7.0, headers=headers) as client:
                response = await client.get(self.api_url, params=params)
                if response.status_code != 200:
                    logger.warning(f"[GDELT] API returned HTTP {response.status_code}. Gracefully continuing.")
                    return []
                
                try:
                    data = response.json()
                except Exception:
                    logger.warning("[GDELT] Failed to decode JSON from GDELT response. Continuing gracefully.")
                    return []

                articles = data.get("articles", [])
                logger.info(f"[GDELT] Retrieved {len(articles)} disaster articles.")

                normalized_items = []
                for art in articles:
                    title = art.get("title") or ""
                    url = art.get("url")
                    if not url or not title:
                        continue

                    # GDELT date format: YYYYMMDDTHHMMSSZ or similar
                    seendate = art.get("seendate")
                    try:
                        dt = date_parser.parse(seendate) if seendate else datetime.now(timezone.utc)
                    except Exception:
                        dt = datetime.now(timezone.utc)

                    domain = art.get("domain") or "GDELT"
                    raw_text = f"{title}\n\nSource: {domain}".strip()

                    item = NormalizedDisasterItem(
                        id=str(uuid.uuid4()),
                        source=f"GDELT ({domain})",
                        source_type="news",
                        timestamp=dt,
                        location_text=None,
                        raw_text=raw_text,
                        url=url,
                        is_mock=False,
                        title=title,
                        raw_metadata={
                            "domain": domain,
                            "language": art.get("language"),
                            "sourcecountry": art.get("sourcecountry")
                        }
                    )
                    normalized_items.append(item)

                return normalized_items

        except httpx.TimeoutException:
            logger.warning("[GDELT] Connection timed out. Graceful fallback activated.")
            return []
        except Exception as e:
            logger.warning(f"[GDELT] Fetch encountered error: {e}. Gracefully continuing.")
            return []
