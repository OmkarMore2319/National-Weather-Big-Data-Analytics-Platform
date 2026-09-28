import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Header,
    Query,
    Request,
    Response,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Ensure the backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Set up logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")

try:
    from .database import init_db, get_db
    from . import crud
    from .schemas import (
        WeatherEvent,
        CitizenReportCreate,
        InternalIngestCreate,
        AdminOverride,
        AdminOverrideCreate,
        AnalyticsSummary,
        AnomalySignal,
        CapAlert,
        CapAlertGenerateRequest,
    )
    from .rate_limiter import rate_limiter
    from .websocket_manager import ws_manager
except ImportError:
    from database import init_db, get_db
    import crud
    from schemas import (
        WeatherEvent,
        CitizenReportCreate,
        InternalIngestCreate,
        AdminOverride,
        AdminOverrideCreate,
        AnalyticsSummary,
        AnomalySignal,
        CapAlert,
        CapAlertGenerateRequest,
    )
    from rate_limiter import rate_limiter
    from websocket_manager import ws_manager


# Import classify_and_score & preload_models from real ml_verification package
from ml_verification import classify_and_score, preload_models


def _serialize_events_for_ml(events):
    return [
        {
            "id": ev.id,
            "source": ev.source,
            "rawText": ev.raw_text,
            "raw_text": ev.raw_text,
            "mediaUrls": ev.media_urls or [],
            "lat": ev.lat,
            "lon": ev.lon,
            "city": ev.city,
            "state": ev.state,
            "eventType": ev.event_type,
            "verificationStatus": ev.verification_status,
            "trustScore": ev.trust_score,
            "duplicateOfId": ev.duplicate_of_id,
            "reportedAt": ev.reported_at.isoformat() if ev.reported_at else None,
            "ingestedAt": ev.ingested_at.isoformat() if ev.ingested_at else None,
        }
        for ev in events
    ]


def _serialize_official_for_ml(readings):
    return [
        {
            "id": off.id,
            "city": off.city,
            "state": off.state,
            "lat": off.lat,
            "lon": off.lon,
            "condition": off.condition,
            "rainfallMm": off.rainfall_mm,
            "tempC": off.temp_c,
            "windKph": off.wind_kph,
            "recordedAt": off.recorded_at.isoformat() if off.recorded_at else None,
        }
        for off in readings
    ]


# Admin authentication configuration
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "secret-admin-token-123")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically initialize SQLite database and tables on startup
    logger.info("Initializing database and tables (WAL mode enabled)...")
    init_db()
    logger.info("Database initialized successfully.")
    preload_models()
    yield


app = FastAPI(
    title="National Weather Big Data Analytics Platform - Backend",
    version="1.0.0",
    description="FastAPI Backend for PS 26069 Weather Ingestion, Verification & Analytics",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_admin_token(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Validates the X-Admin-Token header against ADMIN_TOKEN env var."""
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )
    return x_admin_token


# -----------------------------------------------------------------------------
# WEBSOCKET ENDPOINT
# -----------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint broadcasting WeatherEvent JSON on every insert/update.
    Safely disconnects clients on connection drop.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and receive any incoming ping/messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# -----------------------------------------------------------------------------
# REST ENDPOINTS
# -----------------------------------------------------------------------------
@app.post(
    "/api/v1/reports/citizen",
    response_model=WeatherEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Submit citizen weather report",
)
async def submit_citizen_report(
    report: CitizenReportCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    # 1. Enforce user consent requirement
    if not report.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent must be given to submit a citizen report",
        )

    # 2. Enforce rate limiting: 10 submissions per IP per minute
    rate_limiter.check_rate_limit(request)

    # 3. Fetch context for verification pipeline
    recent_events = crud.get_recent_events(db, hours=24)
    official_readings = crud.get_recent_official_readings(db, hours=24)

    # 4. Classify and verify using real ML verification pipeline
    report_dict = {
        "rawText": report.raw_text,
        "raw_text": report.raw_text,
        "mediaUrls": report.media_urls,
        "media_urls": report.media_urls,
        "lat": report.lat,
        "lon": report.lon,
        "city": report.city,
        "state": report.state,
        "source": "CITIZEN",
    }
    classification = classify_and_score(
        report_dict,
        _serialize_events_for_ml(recent_events),
        _serialize_official_for_ml(official_readings),
    )

    # 5. Persist to database
    event = crud.create_weather_event(
        db=db,
        source="CITIZEN",
        raw_text=report.raw_text,
        media_urls=report.media_urls,
        lat=report.lat,
        lon=report.lon,
        city=report.city,
        state=report.state,
        classification=classification,
        source_meta={},
    )

    # Log every ingested report's id + factorBreakdown to console
    logger.info(
        f"[INGEST] Report ID: {event.id} | Status: {event.verification_status} | "
        f"TrustScore: {event.trust_score} | FactorBreakdown: {event.factor_breakdown}"
    )

    # 6. Broadcast over WebSocket to /ws/live
    event_schema = WeatherEvent.model_validate(event)
    await ws_manager.broadcast_event({
        "type": "event",
        "payload": event_schema.model_dump(by_alias=True, mode="json")
    })

    # Check if this insert crossed an anomaly threshold
    if event.verification_status in ("VERIFIED", "PENDING") and event.city and event.event_type:
        anomaly = crud.check_anomaly_threshold_cross(
            db, city=event.city, state=event.state, event_type=event.event_type
        )
        if anomaly:
            await ws_manager.broadcast_event({
                "type": "anomaly",
                "payload": anomaly.model_dump(by_alias=True, mode="json")
            })

    return event_schema


@app.post(
    "/api/v1/ingest/internal",
    response_model=WeatherEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Internal automated ingestion pipeline",
)
async def ingest_internal(
    report: InternalIngestCreate,
    db: Session = Depends(get_db),
):
    source = report.source
    raw_text = report.raw_text

    # If payload is an OfficialReading (e.g. from official_puller.py)
    if report.condition is not None:
        source = "OFFICIAL_STATION"
        cond = report.condition
        rain = report.rainfall_mm or 0.0
        temp = report.temp_c or 0.0
        wind = report.wind_kph or 0.0
        if not raw_text:
            raw_text = f"Official Station Reading ({report.city}, {report.state}): {cond}, {temp}°C, Rain: {rain}mm, Wind: {wind}km/h"

        from models import OfficialReadingModel
        official_rec = OfficialReadingModel(
            city=report.city or "Unknown",
            state=report.state or "Unknown",
            lat=report.lat,
            lon=report.lon,
            recorded_at=report.recorded_at or datetime.now(timezone.utc),
            condition=cond,
            rainfall_mm=rain,
            temp_c=temp,
            wind_kph=wind,
        )
        db.add(official_rec)
        db.commit()

    if not raw_text:
        raw_text = f"Weather observation at {report.city or 'Unknown'}"

    # Fetch recent context for verification
    recent_events = crud.get_recent_events(db, hours=24)
    official_readings = crud.get_recent_official_readings(db, hours=24)

    # Classify and verify using real ML verification pipeline
    report_dict = {
        "rawText": raw_text,
        "raw_text": raw_text,
        "mediaUrls": report.media_urls,
        "media_urls": report.media_urls,
        "lat": report.lat,
        "lon": report.lon,
        "city": report.city,
        "state": report.state,
        "source": source,
        "sourceMeta": report.source_meta or {},
    }
    classification = classify_and_score(
        report_dict,
        _serialize_events_for_ml(recent_events),
        _serialize_official_for_ml(official_readings),
    )

    # Persist
    event = crud.create_weather_event(
        db=db,
        source=source,
        raw_text=raw_text,
        media_urls=report.media_urls,
        lat=report.lat,
        lon=report.lon,
        city=report.city,
        state=report.state,
        classification=classification,
        source_meta=report.source_meta or {},
    )

    # Log to console
    logger.info(
        f"[INTERNAL INGEST] Report ID: {event.id} | Source: {event.source} | "
        f"Status: {event.verification_status} | TrustScore: {event.trust_score} | "
        f"FactorBreakdown: {event.factor_breakdown}"
    )

    # Broadcast over WebSocket
    event_schema = WeatherEvent.model_validate(event)
    await ws_manager.broadcast_event({
        "type": "event",
        "payload": event_schema.model_dump(by_alias=True, mode="json")
    })

    # Check if this insert crossed an anomaly threshold
    if event.verification_status in ("VERIFIED", "PENDING") and event.city and event.event_type:
        anomaly = crud.check_anomaly_threshold_cross(
            db, city=event.city, state=event.state, event_type=event.event_type
        )
        if anomaly:
            await ws_manager.broadcast_event({
                "type": "anomaly",
                "payload": anomaly.model_dump(by_alias=True, mode="json")
            })

    return event_schema


@app.get(
    "/api/v1/events",
    response_model=List[WeatherEvent],
    summary="List weather events with filtering and pagination",
)
def list_events(
    eventType: Optional[str] = Query(None, alias="eventType"),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_time: Optional[datetime] = Query(None, alias="from"),
    to_time: Optional[datetime] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
):
    events = crud.get_events(
        db=db,
        event_type=eventType,
        state=state,
        city=city,
        status=status,
        from_time=from_time,
        to_time=to_time,
        page=page,
        page_size=pageSize,
    )
    return events


@app.get(
    "/api/v1/events/{id}",
    response_model=WeatherEvent,
    summary="Get single weather event by ID",
)
def get_event(
    id: str,
    db: Session = Depends(get_db),
):
    event = crud.get_event_by_id(db, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weather event with ID {id} not found",
        )
    return event


@app.post(
    "/api/v1/admin/events/{id}/override",
    response_model=AdminOverride,
    summary="Admin override of verification status",
)
async def admin_override_event(
    id: str,
    override_data: AdminOverrideCreate,
    admin_token: str = Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    event = crud.get_event_by_id(db, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weather event with ID {id} not found",
        )

    override = crud.create_admin_override(db, event, override_data)

    logger.info(
        f"[ADMIN OVERRIDE] Event {id}: {override.old_status} -> {override.new_status} "
        f"by {override.admin_username} (Reason: {override.reason})"
    )

    # Broadcast updated event over WebSocket
    event_schema = WeatherEvent.model_validate(event)
    await ws_manager.broadcast_event({
        "type": "event",
        "payload": event_schema.model_dump(by_alias=True, mode="json")
    })

    return override


@app.get(
    "/api/v1/admin/audit-log",
    response_model=List[AdminOverride],
    summary="Get administrative overrides audit log",
)
def get_audit_log(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.get_admin_overrides(db, limit=limit)


@app.post(
    "/api/v1/admin/events/{id}/generate-alert",
    response_model=CapAlert,
    status_code=status.HTTP_201_CREATED,
    summary="Generate CAP v1.2 XML alert for a VERIFIED weather event",
)
def generate_cap_alert(
    id: str,
    req_data: Optional[CapAlertGenerateRequest] = None,
    admin_token: str = Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    event = crud.get_event_by_id(db, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weather event with ID {id} not found",
        )

    if event.verification_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CAP alerts can only be generated from VERIFIED events. Current status is '{event.verification_status}'.",
        )

    admin_username = req_data.admin_username if (req_data and req_data.admin_username) else "admin_officer"
    radius_km = req_data.radius_km if (req_data and req_data.radius_km) else 10.0

    alert_model = crud.create_cap_alert(
        db=db,
        event=event,
        admin_username=admin_username,
        radius_km=radius_km,
    )

    logger.info(
        f"[CAP ALERT GENERATED] Alert ID: {alert_model.id} for Event ID: {id} | "
        f"Severity: {alert_model.severity} | Urgency: {alert_model.urgency} | By: {admin_username}"
    )

    return alert_model


@app.get(
    "/api/v1/admin/alerts",
    response_model=List[CapAlert],
    summary="Get generated CAP alert history",
)
def list_cap_alerts(
    limit: int = Query(100, ge=1, le=500),
    admin_token: str = Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    return crud.get_cap_alerts(db, limit=limit)


@app.get(
    "/api/v1/admin/alerts/{id}/xml",
    summary="Download raw CAP v1.2 XML document",
)
def download_cap_alert_xml(
    id: str,
    admin_token: str = Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    alert = crud.get_cap_alert_by_id(db, id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CAP alert with ID {id} not found",
        )

    return Response(
        content=alert.xml_payload,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="cap_alert_{id}.xml"'
        },
    )


@app.get(
    "/api/v1/analytics/summary",
    response_model=AnalyticsSummary,
    summary="Get aggregated analytics summary metrics",
)
def get_analytics_summary(
    db: Session = Depends(get_db),
):
    return crud.get_analytics_summary(db)


@app.get(
    "/api/v1/analytics/anomalies",
    response_model=List[AnomalySignal],
    summary="Get active anomaly detection signals",
)
def get_anomalies(
    windowHours: int = Query(3, alias="windowHours"),
    threshold: int = Query(5, alias="threshold"),
    db: Session = Depends(get_db),
):
    return crud.compute_anomalies(db, window_hours=windowHours, threshold=threshold)


@app.get("/")
def root():
    """Root endpoint welcoming users and pointing to docs."""
    return {
        "message": "National Weather Big Data Analytics Platform API (PS 26069)",
        "docs": "/docs",
        "health": "/api/v1/health",
        "analytics": "/api/v1/analytics/summary",
        "events": "/api/v1/events",
        "frontend": "http://localhost:5173"
    }


@app.get("/api/v1/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "weather-backend"}

