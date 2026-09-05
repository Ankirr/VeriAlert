import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class NormalizedDisasterItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    source_type: str  # 'news_api', 'rss_feed', 'gov_alert', 'social_media'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_text: str
    title: Optional[str] = None
    url: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

class DisasterItemCreate(BaseModel):
    source: str
    source_type: str
    timestamp: datetime
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_text: str
    title: Optional[str] = None
    url: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
