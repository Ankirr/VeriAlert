import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Agent AI Disaster Framework"
    DATABASE_URL: str = "sqlite+aiosqlite:///./disaster_app.db"
    
    # API keys and endpoints for real sources (with free defaults & fallbacks)
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    NWS_API_URL: str = os.getenv("NWS_API_URL", "https://api.weather.gov/alerts/active?status=actual&severity=Severe,Extreme")
    GDACS_RSS_URL: str = os.getenv("GDACS_RSS_URL", "https://www.gdacs.org/xml/rss.xml")
    
    # Social Media API configuration (Twitter/X API or Mastodon Public Tag Stream)
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")
    MASTODON_SERVER: str = os.getenv("MASTODON_SERVER", "https://mastodon.social")
    MASTODON_DISASTER_HASHTAG: str = os.getenv("MASTODON_DISASTER_HASHTAG", "disaster")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

