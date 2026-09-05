import logging
from datetime import datetime, timezone, timedelta
from typing import List
from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

MOCK_SOCIAL_POSTS = [
    {
        "post_id": "tweet_102938481",
        "username": "@boulder_resident99",
        "platform": "X (Twitter) Stream Mock",
        "text": "OMG huge smoke column near Marshall Mesa in Boulder! Winds are insane right now, police ordering evacs #BoulderFire #Wildfire",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(),
        "location": "Boulder, CO",
        "lat": 40.0150,
        "lon": -105.2705,
        "url": "https://x.com/boulder_resident99/status/102938481"
    },
    {
        "post_id": "tweet_102938482",
        "username": "@manila_commuter",
        "platform": "X (Twitter) Stream Mock",
        "text": "Flood water is up to waist high near Espana Blvd Manila! Cars are stranded. Stay away from the area! #ManilaFlood #CarinaPH",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
        "location": "Manila, Philippines",
        "lat": 14.5995,
        "lon": 120.9842,
        "url": "https://x.com/manila_commuter/status/102938482"
    },
    {
        "post_id": "tweet_102938483",
        "username": "@tech_blogger_guy",
        "platform": "X (Twitter) Stream Mock",
        "text": "Just launched my new React JS tutorial! Check out the code repository link below #coding #reactjs #webdev",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
        "location": "San Francisco, CA",
        "lat": 37.7749,
        "lon": -122.4194,
        "url": "https://x.com/tech_blogger_guy/status/102938483"
    },
    {
        "post_id": "tweet_102938484",
        "username": "@norcal_spotter",
        "platform": "X (Twitter) Stream Mock",
        "text": "Whoa strong earthquake just shook Eureka and Ferndale! Everything on my shelf fell off. Anyone else feel that? #CalEarthquake",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat(),
        "location": "Ferndale, CA",
        "lat": 40.5762,
        "lon": -124.2639,
        "url": "https://x.com/norcal_spotter/status/102938484"
    }
]

class MockSocialMediaCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="Mock Social Media Stream", source_type="social_media")

    async def fetch(self) -> List[NormalizedDisasterItem]:
        logger.info("Fetching mock social media posts...")
        items: List[NormalizedDisasterItem] = []

        for post in MOCK_SOCIAL_POSTS:
            dt = datetime.fromisoformat(post["timestamp"])
            item = NormalizedDisasterItem(
                source=post["platform"],
                source_type=self.source_type,
                timestamp=dt,
                location_name=post["location"],
                latitude=post["lat"],
                longitude=post["lon"],
                raw_text=post["text"],
                title=f"Post by {post['username']}",
                url=post["url"],
                raw_metadata={
                    "post_id": post["post_id"],
                    "username": post["username"],
                    "platform": post["platform"]
                }
            )
            items.append(item)

        return items
