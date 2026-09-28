import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, ForeignKey
try:
    from .database import Base
except ImportError:
    from database import Base



def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WeatherEventModel(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    source = Column(String(30), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    media_urls = Column(JSON, nullable=False, default=list)
    reported_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    classification_confidence = Column(Float, nullable=False, default=0.0)
    verification_status = Column(String(30), nullable=False, index=True, default="PENDING")
    trust_score = Column(Float, nullable=False, default=0.0)
    factor_breakdown = Column(JSON, nullable=False, default=dict)
    corroboration_count = Column(Integer, nullable=False, default=0)
    duplicate_of_id = Column(String(36), nullable=True, index=True)
    source_meta = Column(JSON, nullable=False, default=dict)


class OfficialReadingModel(Base):
    __tablename__ = "official_readings"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    condition = Column(String(100), nullable=False)
    rainfall_mm = Column(Float, nullable=False, default=0.0)
    temp_c = Column(Float, nullable=False, default=0.0)
    wind_kph = Column(Float, nullable=False, default=0.0)


class AdminOverrideModel(Base):
    __tablename__ = "admin_overrides"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    admin_username = Column(String(100), nullable=False)
    old_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)


class CapAlertModel(Base):
    __tablename__ = "cap_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    identifier = Column(String(100), nullable=False, index=True)
    sender = Column(String(100), nullable=False)
    sent = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    status = Column(String(30), nullable=False, default="Actual")
    msg_type = Column(String(30), nullable=False, default="Alert")
    scope = Column(String(30), nullable=False, default="Public")
    category = Column(String(30), nullable=False, default="Met")
    event = Column(String(100), nullable=False)
    urgency = Column(String(30), nullable=False)
    severity = Column(String(30), nullable=False)
    certainty = Column(String(30), nullable=False)
    headline = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    instruction = Column(Text, nullable=False)
    area_desc = Column(Text, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    radius_km = Column(Float, nullable=False, default=10.0)
    xml_payload = Column(Text, nullable=False)
    generated_by = Column(String(100), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

