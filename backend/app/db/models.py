from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, Boolean, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class RawDisasterItemModel(Base):
    """
    Database table storing normalized disaster items from all collectors.
    Complies with required schema: {id, source, source_type, timestamp, location_text, raw_text, url, is_mock}
    """
    __tablename__ = "raw_disaster_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True, unique=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Enrichment fields (Phase 2 & 3)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Verification & Clustering fields (Phase 4)
    cluster_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_band: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def to_dict(self):
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
            "cluster_id": self.cluster_id,
            "trust_score": self.trust_score,
            "trust_band": self.trust_band,
            "raw_metadata": self.raw_metadata,
        }

class DisasterClusterModel(Base):
    """
    Database table storing semantic incident clusters with NLI veracity verification
    and deterministic trust scores.
    """
    __tablename__ = "disaster_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_name: Mapped[str] = mapped_column(String(500), index=True)
    disaster_type: Mapped[str] = mapped_column(String(50), index=True)
    location_name: Mapped[str] = mapped_column(String(255), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    
    # Veracity & Trust metrics
    trust_score: Mapped[float] = mapped_column(Float, index=True)
    trust_band: Mapped[str] = mapped_column(String(50), index=True)
    source_authority_score: Mapped[float] = mapped_column(Float)
    corroborating_sources_count: Mapped[int] = mapped_column(Integer, default=1)
    has_contradiction: Mapped[bool] = mapped_column(Boolean, default=False)
    nli_agreement_score: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Metadata & Relations
    sources: Mapped[list] = mapped_column(JSON, default=list)
    item_ids: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # Populated in Phase 5
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "event_name": self.event_name,
            "disaster_type": self.disaster_type,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "trust_score": round(self.trust_score, 4),
            "trust_band": self.trust_band,
            "source_authority_score": round(self.source_authority_score, 4),
            "corroborating_sources_count": self.corroborating_sources_count,
            "has_contradiction": self.has_contradiction,
            "nli_agreement_score": round(self.nli_agreement_score, 4),
            "sources": self.sources,
            "item_ids": self.item_ids,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
