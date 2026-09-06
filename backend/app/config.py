import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Agent AI Disaster Framework"
    DATABASE_URL: str = "postgresql+asyncpg://disaster_user:disaster_pass@localhost:5432/disaster_db"
    DATABASE_URL_SYNC: str = "postgresql://disaster_user:disaster_pass@localhost:5432/disaster_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API credentials
    NEWSAPI_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "DisasterMonitor/1.0 (by /u/VeriAlert)"
    
    # Geocoding & Basemaps
    NOMINATIM_USER_AGENT: str = "VeriAlertDisasterApp/1.0"
    CARTO_API_KEY: str = "cb1_2y6r_1_4449aee82478330890c3942b"

    model_config = SettingsConfigDict(
        env_file=[
            str(backend_dir / ".env"),
            str(root_dir / ".env"),
            ".env"
        ],
        extra="ignore"
    )

settings = Settings()
