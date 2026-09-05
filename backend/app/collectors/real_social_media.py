import logging
from datetime import datetime, timezone
from typing import List
import httpx

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem
from app.config import settings
from app.collectors.mock_social_media import MOCK_SOCIAL_POSTS

logger = logging.getLogger(__name__)

class RealSocialMediaCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="Live Social Media Disaster Monitor (X API / Mastodon Feed)", source_type="social_media")
        self.twitter_bearer_token = settings.TWITTER_BEARER_TOKEN
        self.mastodon_server = settings.MASTODON_SERVER
        self.hashtag = settings.MASTODON_DISASTER_HASHTAG

    async def fetch(self) -> List[NormalizedDisasterItem]:
        logger.info("Fetching real social media posts (X API / Mastodon open tag stream)...")
        items: List[NormalizedDisasterItem] = []

        # 1. Try Twitter/X API v2 if Bearer Token is provided
        if self.twitter_bearer_token:
            try:
                url = "https://api.twitter.com/2/tweets/search/recent?query=(wildfire OR earthquake OR flood OR hurricane) -is:retweet&tweet.fields=created_at,geo,author_id"
                headers = {"Authorization": f"Bearer {self.twitter_bearer_token}"}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        tweets = data.get("data", [])
                        logger.info(f"X (Twitter) API v2 returned {len(tweets)} tweets.")
                        for tweet in tweets:
                            created_at = tweet.get("created_at")
                            ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.now(timezone.utc)
                            items.append(NormalizedDisasterItem(
                                source="X (Twitter) Live Stream",
                                source_type=self.source_type,
                                timestamp=ts,
                                location_name="Twitter Geo",
                                latitude=None,
                                longitude=None,
                                raw_text=tweet.get("text", ""),
                                title=f"Tweet by User {tweet.get('author_id', 'Unknown')}",
                                url=f"https://x.com/i/web/status/{tweet.get('id')}",
                                raw_metadata={"tweet_id": tweet.get("id"), "platform": "X (Twitter)"}
                            ))
            except Exception as e:
                logger.warning(f"Failed to query Twitter/X API v2: {e}")

        # 2. Try Open Mastodon Public Hashtag Stream (Free, open-source, no API key required)
        if not items:
            try:
                mastodon_url = f"{self.mastodon_server}/api/v1/timelines/tag/{self.hashtag}?limit=10"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(mastodon_url)
                    if resp.status_code == 200:
                        posts = resp.json()
                        logger.info(f"Mastodon public stream returned {len(posts)} social posts.")
                        for post in posts:
                            created_at = post.get("created_at")
                            ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.now(timezone.utc)
                            # Strip basic HTML tags from post content
                            raw_content = post.get("content", "").replace("<p>", "").replace("</p>", "").replace("<br />", "\n")
                            account = post.get("account", {})
                            items.append(NormalizedDisasterItem(
                                source=f"Mastodon (@{account.get('username', 'user')})",
                                source_type=self.source_type,
                                timestamp=ts,
                                location_name="Federated Network",
                                latitude=None,
                                longitude=None,
                                raw_text=raw_content,
                                title=f"Post by @{account.get('username', 'user')}",
                                url=post.get("url"),
                                raw_metadata={
                                    "post_id": post.get("id"),
                                    "username": account.get("username"),
                                    "platform": "Mastodon"
                                }
                            ))
            except Exception as e:
                logger.warning(f"Could not fetch Mastodon social stream: {e}")

        # 3. Fallback to Mock Payload if no items retrieved
        if not items:
            logger.info("No live social media API responses. Utilizing fallback mock payload.")
            for post in MOCK_SOCIAL_POSTS:
                dt = datetime.fromisoformat(post["timestamp"])
                items.append(NormalizedDisasterItem(
                    source=post["platform"],
                    source_type=self.source_type,
                    timestamp=dt,
                    location_name=post["location"],
                    latitude=post["lat"],
                    longitude=post["lon"],
                    raw_text=post["text"],
                    title=f"Post by {post['username']}",
                    url=post["url"],
                    raw_metadata={"post_id": post["post_id"], "platform": post["platform"], "fallback": True}
                ))

        return items
