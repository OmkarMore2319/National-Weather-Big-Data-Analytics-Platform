from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically aliases snake_case to camelCase."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


SourceType = Literal["CITIZEN", "SOCIAL_SIMULATED", "SOCIAL_REAL", "NEWS_RSS", "OFFICIAL_STATION"]
EventType = Literal[
    "RAINFALL",
    "THUNDERSTORM",
    "FLOODING",
    "HEATWAVE",
    "FOG",
    "DUST_STORM",
    "STRONG_WIND",
    "UNKNOWN",
]
VerificationStatus = Literal["PENDING", "VERIFIED", "SUSPICIOUS", "REJECTED", "DUPLICATE"]


class FactorBreakdown(CamelModel):
    source_trust: float = 0.0
    corroboration_boost: float = 0.0
    cross_match_official: float = 0.0
    image_check: float = 0.0


class WeatherEvent(CamelModel):
    id: str
    source: SourceType
    raw_text: str
    media_urls: List[str] = Field(default_factory=list)
    reported_at: datetime
    ingested_at: datetime
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    city: Optional[str] = None
    state: Optional[str] = None
    event_type: EventType = "UNKNOWN"
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_status: VerificationStatus = "PENDING"
    trust_score: float = Field(default=0.0, ge=0.0, le=100.0)
    factor_breakdown: Dict[str, Any] = Field(default_factory=dict)
    corroboration_count: int = 0
    duplicate_of_id: Optional[str] = None
    source_meta: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("reported_at", "ingested_at")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()




class CitizenReportCreate(CamelModel):
    raw_text: str
    media_urls: List[str] = Field(default_factory=list)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    city: Optional[str] = None
    state: Optional[str] = None
    consent_given: bool = Field(..., description="Must be true to submit report")


class InternalIngestCreate(CamelModel):
    raw_text: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    city: Optional[str] = None
    state: Optional[str] = None
    source: SourceType = "CITIZEN"
    source_meta: Optional[Dict[str, Any]] = None

    # Extended fields when OfficialReading is sent directly to internal ingest
    condition: Optional[str] = None
    rainfall_mm: Optional[float] = None
    temp_c: Optional[float] = None
    wind_kph: Optional[float] = None
    recorded_at: Optional[datetime] = None



class AdminOverrideCreate(CamelModel):
    admin_username: str
    new_status: VerificationStatus
    reason: str


class AdminOverride(CamelModel):
    id: str
    event_id: str
    admin_username: str
    old_status: str
    new_status: str
    reason: str
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class OfficialReadingBase(CamelModel):
    city: str
    state: str
    lat: float
    lon: float
    condition: str
    rainfall_mm: float = 0.0
    temp_c: float = 0.0
    wind_kph: float = 0.0


class OfficialReading(OfficialReadingBase):
    id: str
    recorded_at: datetime

    @field_serializer("recorded_at")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()



class AnalyticsSummary(CamelModel):
    total_today: int
    pct_verified: float
    top_event_type: str
    most_affected_state: str
    by_event_type: Dict[str, int]
    by_status: Dict[str, int]


AnomalySeverity = Literal["WATCH", "ALERT"]


class AnomalySignal(CamelModel):
    city: str
    state: Optional[str] = None
    event_type: str
    window_hours: int = 3
    report_count: int
    threshold: int = 5
    severity: AnomalySeverity = "WATCH"
    detected_at: datetime

    @field_serializer("detected_at")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class CapAlertGenerateRequest(CamelModel):
    admin_username: Optional[str] = "admin_officer"
    radius_km: Optional[float] = 10.0


class CapAlert(CamelModel):
    id: str
    event_id: str
    identifier: str
    sender: str
    sent: datetime
    status: str = "Actual"
    msg_type: str = "Alert"
    scope: str = "Public"
    category: str = "Met"
    event: str
    urgency: str
    severity: str
    certainty: str
    headline: str
    description: str
    instruction: str
    area_desc: str
    lat: float
    lon: float
    radius_km: float = 10.0
    xml_payload: str
    generated_by: str
    generated_at: datetime

    @field_serializer("sent", "generated_at")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


