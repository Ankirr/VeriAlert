import logging
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List

from app.collectors.base import BaseCollector
from app.models.schemas import NormalizedDisasterItem
from app.config import settings

logger = logging.getLogger(__name__)

MOCK_REDDIT_POSTS = [
    {
        "title": "Flooding in Kurla and Dadar after intense cloudburst in Mumbai",
        "selftext": "Water is knee-deep near the station. Local trains on Central Line running 30 mins late. Stay indoors guys!",
        "subreddit": "mumbai",
        "url": "https://www.reddit.com/r/mumbai/comments/mock_mumbai_flood_01",
        "author": "local_commuter_99"
    },
    {
        "title": "Massive dust storm hitting parts of Delhi NCR right now, visibility dropped near zero",
        "selftext": "High winds recorded over 60 km/h in Noida and South Delhi. Trees fallen on Ring Road. Drive safe!",
        "subreddit": "delhi",
        "url": "https://www.reddit.com/r/delhi/comments/mock_delhi_storm_02",
        "author": "delhi_resident_42"
    },
    {
        "title": "Earthquake tremors felt in Guwahati, Assam around 2 minutes ago",
        "selftext": "Felt strong shaking on 4th floor. Fan swaying. Anyone else felt it? Hope everyone is safe.",
        "subreddit": "assam",
        "url": "https://www.reddit.com/r/assam/comments/mock_assam_quake_03",
        "author": "northeast_watcher"
    },
    {
        "title": "Severe waterlogging on Outer Ring Road, Bengaluru after overnight rains",
        "selftext": "EcoSpace and Bellandur junction completely jammed. Several vehicles stalled in water.",
        "subreddit": "bangalore",
        "url": "https://www.reddit.com/r/bangalore/comments/mock_blr_flood_04",
        "author": "techie_on_road"
    }
]

class RedditCollector(BaseCollector):
    """
    Reddit disaster collector using PRAW with automatic graceful mock fallback.
    If REDDIT_CLIENT_ID / SECRET are valid, pulls live posts from disaster/weather subreddits.
    Otherwise, provides realistic mock Reddit items tagged is_mock=True.
    Normalized into unified schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}.
    """
    def __init__(self):
        super().__init__(source_name="Reddit", source_type="social")
        self.subreddits = ["disasters", "naturaldisasters", "weather"]

    async def fetch(self) -> List[NormalizedDisasterItem]:
        client_id = settings.REDDIT_CLIENT_ID
        client_secret = settings.REDDIT_CLIENT_SECRET
        user_agent = settings.REDDIT_USER_AGENT

        # If keys are placeholder or empty, use mock fallback gracefully
        if not client_id or not client_secret or "your_reddit" in client_id or "your_reddit" in client_secret:
            logger.info("[Reddit] No active Reddit API credentials detected in .env. Using mock fallback data (is_mock=True).")
            return self._get_mock_items()

        # Attempt live PRAW collection in async executor thread
        try:
            loop = asyncio.get_running_loop()
            items = await loop.run_in_executor(None, self._fetch_live_reddit, client_id, client_secret, user_agent)
            if items:
                return items
            logger.warning("[Reddit] Live fetch yielded 0 items. Using mock fallback.")
            return self._get_mock_items()
        except Exception as e:
            logger.warning(f"[Reddit] Live PRAW fetch failed ({e}). Gracefully falling back to mock data.")
            return self._get_mock_items()

    def _fetch_live_reddit(self, client_id: str, client_secret: str, user_agent: str) -> List[NormalizedDisasterItem]:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        items = []
        for sub_name in self.subreddits:
            try:
                sub = reddit.subreddit(sub_name)
                for submission in sub.hot(limit=5):
                    if submission.stickied:
                        continue
                    
                    title = submission.title or ""
                    selftext = submission.selftext or ""
                    raw_text = f"{title}\n\n{selftext}".strip()
                    url = f"https://www.reddit.com{submission.permalink}"
                    dt = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)

                    item = NormalizedDisasterItem(
                        id=str(uuid.uuid4()),
                        source=f"Reddit (r/{sub_name})",
                        source_type="social",
                        timestamp=dt,
                        location_text=None,
                        raw_text=raw_text,
                        url=url,
                        is_mock=False,
                        title=title,
                        raw_metadata={
                            "author": str(submission.author),
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "subreddit": sub_name
                        }
                    )
                    items.append(item)
            except Exception as ex:
                logger.warning(f"[Reddit] Error querying r/{sub_name}: {ex}")
                continue

        return items

    def _get_mock_items(self) -> List[NormalizedDisasterItem]:
        items = []
        for post in MOCK_REDDIT_POSTS:
            raw_text = f"{post['title']}\n\n{post['selftext']}"
            item = NormalizedDisasterItem(
                id=str(uuid.uuid4()),
                source=f"Reddit (r/{post['subreddit']} - MOCK)",
                source_type="social",
                timestamp=datetime.now(timezone.utc),
                location_text=None,
                raw_text=raw_text,
                url=post["url"],
                is_mock=True,
                title=post["title"],
                raw_metadata={
                    "author": post["author"],
                    "subreddit": post["subreddit"],
                    "note": "Mock item generated for Phase 1 pending Reddit API developer approval"
                }
            )
            items.append(item)
        return items
