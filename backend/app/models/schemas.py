import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class NormalizedDisasterItem(BaseModel):
    """
    Unified normalized schema across all data ingestion sources:
    {id, source, source_type, timestamp, location_text, raw_text, url, is_mock (boolean)}
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    source_type: str  # 'news', 'social', 'rss', 'official'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location_text: Optional[str] = None
    raw_text: str
    url: Optional[str] = None
    is_mock: bool = False
    
    # Optional extensions for subsequent pipeline stages (Phase 3 Geo-Extraction & Phase 2 NLP)
    title: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_type": self.source_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "location_text": self.location_text,
            "raw_text": self.raw_text,
            "url": self.url,
            "is_mock": self.is_mock,
            "title": self.title,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "raw_metadata": self.raw_metadata,
        }
