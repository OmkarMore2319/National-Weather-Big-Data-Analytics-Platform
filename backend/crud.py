import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

try:
    from .models import WeatherEventModel, OfficialReadingModel, AdminOverrideModel, CapAlertModel
    from .schemas import (
        CitizenReportCreate,
        InternalIngestCreate,
        AdminOverrideCreate,
        AnomalySignal,
        CapAlert,
    )
except ImportError:
    from models import WeatherEventModel, OfficialReadingModel, AdminOverrideModel, CapAlertModel
    from schemas import (
        CitizenReportCreate,
        InternalIngestCreate,
        AdminOverrideCreate,
        AnomalySignal,
        CapAlert,
    )



def get_recent_events(db: Session, hours: int = 24) -> List[WeatherEventModel]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.query(WeatherEventModel).filter(WeatherEventModel.reported_at >= cutoff).all()


def get_recent_official_readings(db: Session, hours: int = 24) -> List[OfficialReadingModel]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.query(OfficialReadingModel).filter(OfficialReadingModel.recorded_at >= cutoff).all()


def create_weather_event(
    db: Session,
    source: str,
    raw_text: str,
    media_urls: List[str],
    lat: float,
    lon: float,
    city: Optional[str],
    state: Optional[str],
    classification: Dict[str, Any],
    source_meta: Optional[Dict[str, Any]] = None,
    reported_at: Optional[datetime] = None,
) -> WeatherEventModel:
    now = datetime.now(timezone.utc)
    if reported_at is None:
        reported_at = now

    event = WeatherEventModel(
        source=source,
        raw_text=raw_text,
        media_urls=media_urls or [],
        reported_at=reported_at,
        ingested_at=now,
        lat=lat,
        lon=lon,
        city=city,
        state=state,
        event_type=classification.get("eventType") or classification.get("event_type", "UNKNOWN"),
        classification_confidence=classification.get("classificationConfidence") or classification.get("classification_confidence", 0.0),
        verification_status=classification.get("verificationStatus") or classification.get("verification_status", "PENDING"),
        trust_score=classification.get("trustScore") if classification.get("trustScore") is not None else classification.get("trust_score", 0.0),
        factor_breakdown=classification.get("factorBreakdown") or classification.get("factor_breakdown", {}),
        corroboration_count=classification.get("corroborationCount") if classification.get("corroborationCount") is not None else classification.get("corroboration_count", 0),
        duplicate_of_id=classification.get("duplicateOfId") or classification.get("duplicate_of_id"),
        source_meta=source_meta or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_events(
    db: Session,
    event_type: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> List[WeatherEventModel]:
    query = db.query(WeatherEventModel)

    if event_type:
        query = query.filter(WeatherEventModel.event_type == event_type.upper())
    if state:
        query = query.filter(func.lower(WeatherEventModel.state) == state.lower().strip())
    if city:
        query = query.filter(func.lower(WeatherEventModel.city) == city.lower().strip())
    if status:
        query = query.filter(WeatherEventModel.verification_status == status.upper().strip())
    if from_time:
        query = query.filter(WeatherEventModel.reported_at >= from_time)
    if to_time:
        query = query.filter(WeatherEventModel.reported_at <= to_time)

    # Order by newest first
    query = query.order_by(desc(WeatherEventModel.reported_at))

    # Pagination
    if page < 1:
        page = 1
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size).all()


def get_event_by_id(db: Session, event_id: str) -> Optional[WeatherEventModel]:
    return db.query(WeatherEventModel).filter(WeatherEventModel.id == event_id).first()


def create_admin_override(
    db: Session,
    event: WeatherEventModel,
    override_data: AdminOverrideCreate,
) -> AdminOverrideModel:
    old_status = event.verification_status
    event.verification_status = override_data.new_status
    now = datetime.now(timezone.utc)

    override = AdminOverrideModel(
        event_id=event.id,
        admin_username=override_data.admin_username,
        old_status=old_status,
        new_status=override_data.new_status,
        reason=override_data.reason,
        timestamp=now,
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    db.refresh(event)
    return override


def get_admin_overrides(db: Session, limit: int = 100) -> List[AdminOverrideModel]:
    return db.query(AdminOverrideModel).order_by(desc(AdminOverrideModel.timestamp)).limit(limit).all()


def get_analytics_summary(db: Session) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    # Total today
    total_today = (
        db.query(func.count(WeatherEventModel.id))
        .filter(WeatherEventModel.ingested_at >= start_of_today)
        .scalar()
        or 0
    )

    # All events count
    total_all = db.query(func.count(WeatherEventModel.id)).scalar() or 0

    # Verification counts
    verified_count = (
        db.query(func.count(WeatherEventModel.id))
        .filter(WeatherEventModel.verification_status == "VERIFIED")
        .scalar()
        or 0
    )

    pct_verified = round((verified_count / total_all * 100.0), 1) if total_all > 0 else 0.0

    # By Event Type
    by_event_type_rows = (
        db.query(WeatherEventModel.event_type, func.count(WeatherEventModel.id))
        .group_by(WeatherEventModel.event_type)
        .all()
    )
    by_event_type = {row[0]: row[1] for row in by_event_type_rows}

    # Top Event Type
    top_event_type = "UNKNOWN"
    if by_event_type:
        top_event_type = max(by_event_type.items(), key=lambda x: x[1])[0]

    # Most Affected State
    most_affected_row = (
        db.query(WeatherEventModel.state, func.count(WeatherEventModel.id))
        .filter(WeatherEventModel.state.isnot(None))
        .group_by(WeatherEventModel.state)
        .order_by(desc(func.count(WeatherEventModel.id)))
        .first()
    )
    most_affected_state = most_affected_row[0] if most_affected_row and most_affected_row[0] else "N/A"

    # By Status
    by_status_rows = (
        db.query(WeatherEventModel.verification_status, func.count(WeatherEventModel.id))
        .group_by(WeatherEventModel.verification_status)
        .all()
    )
    by_status = {row[0]: row[1] for row in by_status_rows}

    return {
        "total_today": total_today,
        "pct_verified": pct_verified,
        "top_event_type": top_event_type,
        "most_affected_state": most_affected_state,
        "by_event_type": by_event_type,
        "by_status": by_status,
    }


def compute_anomalies(
    db: Session,
    window_hours: int = 3,
    threshold: int = 5,
) -> List[AnomalySignal]:
    """
    Groups existing WeatherEvent rows by (city, eventType) for events with
    reportedAt within the last windowHours (default 3 hours).
    Only counts events with verificationStatus in ('VERIFIED', 'PENDING').
    For each group where reportCount >= threshold (default 5), emits an AnomalySignal
    with severity='WATCH'. If reportCount >= threshold*2, severity='ALERT' instead.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    results = (
        db.query(
            WeatherEventModel.city,
            func.max(WeatherEventModel.state).label("state"),
            WeatherEventModel.event_type,
            func.count(WeatherEventModel.id).label("report_count"),
        )
        .filter(
            WeatherEventModel.reported_at >= cutoff,
            WeatherEventModel.verification_status.in_(["VERIFIED", "PENDING"]),
            WeatherEventModel.city.isnot(None),
            WeatherEventModel.city != "",
        )
        .group_by(WeatherEventModel.city, WeatherEventModel.event_type)
        .having(func.count(WeatherEventModel.id) >= threshold)
        .all()
    )

    now = datetime.now(timezone.utc)
    anomalies: List[AnomalySignal] = []
    for city, state, event_type, report_count in results:
        severity = "ALERT" if report_count >= threshold * 2 else "WATCH"
        anomalies.append(
            AnomalySignal(
                city=city,
                state=state,
                event_type=event_type,
                window_hours=window_hours,
                report_count=report_count,
                threshold=threshold,
                severity=severity,
                detected_at=now,
            )
        )
    return anomalies


def check_anomaly_threshold_cross(
    db: Session,
    city: str,
    state: Optional[str],
    event_type: str,
    window_hours: int = 3,
    threshold: int = 5,
) -> Optional[AnomalySignal]:
    """
    Checks if a newly ingested event for (city, event_type) just crossed the
    anomaly threshold (threshold for WATCH or threshold*2 for ALERT).
    Returns the AnomalySignal if triggered, else None.
    """
    if not city or not event_type:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    count = (
        db.query(func.count(WeatherEventModel.id))
        .filter(
            func.lower(WeatherEventModel.city) == city.lower().strip(),
            WeatherEventModel.event_type == event_type.upper().strip(),
            WeatherEventModel.reported_at >= cutoff,
            WeatherEventModel.verification_status.in_(["VERIFIED", "PENDING"]),
        )
        .scalar()
    ) or 0

    if count == threshold or count == threshold * 2:
        severity = "ALERT" if count >= threshold * 2 else "WATCH"
        return AnomalySignal(
            city=city,
            state=state,
            event_type=event_type,
            window_hours=window_hours,
            report_count=count,
            threshold=threshold,
            severity=severity,
            detected_at=datetime.now(timezone.utc),
        )
    return None


EVENT_HUMAN_NAMES = {
    "RAINFALL": "Heavy Rainfall",
    "THUNDERSTORM": "Severe Thunderstorm",
    "FLOODING": "Flash Flood",
    "HEATWAVE": "Heat Wave",
    "FOG": "Dense Fog",
    "DUST_STORM": "Dust Storm",
    "STRONG_WIND": "Strong Wind Warning",
}

EVENT_INSTRUCTIONS = {
    "FLOODING": "Avoid low-lying areas and do not attempt to cross flooded roads.",
    "HEATWAVE": "Stay hydrated and avoid outdoor activity during peak afternoon hours.",
    "RAINFALL": "Drive with extreme caution and prepare for poor visibility and potential waterlogging.",
    "THUNDERSTORM": "Seek indoor shelter immediately; stay away from electrical appliances and trees.",
    "FOG": "Use low-beam headlights while driving and maintain a safe distance from other vehicles.",
    "DUST_STORM": "Stay indoors, close windows and doors, and wear a mask if outside.",
    "STRONG_WIND": "Secure loose outdoor objects and stay clear of trees and power lines.",
}


def build_cap_v12_xml(
    identifier: str,
    sender: str,
    sent_iso: str,
    status: str,
    msg_type: str,
    scope: str,
    category: str,
    event_name: str,
    urgency: str,
    severity: str,
    certainty: str,
    headline: str,
    description: str,
    instruction: str,
    area_desc: str,
    lat: float,
    lon: float,
    radius_km: float,
) -> str:
    root = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
    ET.SubElement(root, "identifier").text = identifier
    ET.SubElement(root, "sender").text = sender
    ET.SubElement(root, "sent").text = sent_iso
    ET.SubElement(root, "status").text = status
    ET.SubElement(root, "msgType").text = msg_type
    ET.SubElement(root, "scope").text = scope

    info = ET.SubElement(root, "info")
    ET.SubElement(info, "category").text = category
    ET.SubElement(info, "event").text = event_name
    ET.SubElement(info, "urgency").text = urgency
    ET.SubElement(info, "severity").text = severity
    ET.SubElement(info, "certainty").text = certainty
    ET.SubElement(info, "headline").text = headline
    ET.SubElement(info, "description").text = description
    ET.SubElement(info, "instruction").text = instruction

    area = ET.SubElement(info, "area")
    ET.SubElement(area, "areaDesc").text = area_desc
    ET.SubElement(area, "circle").text = f"{lat:.4f},{lon:.4f} {radius_km:.1f}"

    try:
        ET.indent(root, space="  ")
    except AttributeError:
        pass

    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    return xml_header + ET.tostring(root, encoding="utf-8").decode("utf-8")


def create_cap_alert(
    db: Session,
    event: WeatherEventModel,
    admin_username: str = "admin_officer",
    radius_km: float = 10.0,
) -> CapAlertModel:
    event_type_str = (event.event_type or "UNKNOWN").upper()
    event_name = EVENT_HUMAN_NAMES.get(event_type_str, "Weather Warning")

    # urgency: Immediate if trustScore >= 85, else Expected
    urgency = "Immediate" if (event.trust_score or 0) >= 85 else "Expected"

    # severity: Extreme if trustScore >= 90, Severe if trustScore >= 70, else Moderate
    if (event.trust_score or 0) >= 90:
        severity = "Extreme"
    elif (event.trust_score or 0) >= 70:
        severity = "Severe"
    else:
        severity = "Moderate"

    # certainty: Observed if source == OFFICIAL_STATION or corroborationCount >= 3, else Likely
    if event.source == "OFFICIAL_STATION" or (event.corroboration_count or 0) >= 3:
        certainty = "Observed"
    else:
        certainty = "Likely"

    category = "Met"
    city_str = event.city or "Region"
    state_str = event.state or "India"
    headline = f"{event_name} reported in {city_str}, {state_str}"

    description = event.raw_text or headline
    if len(description) > 500:
        description = description[:497] + "..."

    instruction = EVENT_INSTRUCTIONS.get(
        event_type_str,
        "Stay informed via official meteorological bulletins and take necessary safety precautions."
    )

    area_desc = f"{city_str}, {state_str}, India"
    identifier = str(uuid.uuid4())
    sender = "prototype@weather-platform.demo"
    now = datetime.now(timezone.utc)
    sent_iso = now.isoformat()

    xml_payload = build_cap_v12_xml(
        identifier=identifier,
        sender=sender,
        sent_iso=sent_iso,
        status="Actual",
        msg_type="Alert",
        scope="Public",
        category=category,
        event_name=event_name,
        urgency=urgency,
        severity=severity,
        certainty=certainty,
        headline=headline,
        description=description,
        instruction=instruction,
        area_desc=area_desc,
        lat=event.lat,
        lon=event.lon,
        radius_km=radius_km,
    )

    alert_model = CapAlertModel(
        event_id=event.id,
        identifier=identifier,
        sender=sender,
        sent=now,
        status="Actual",
        msg_type="Alert",
        scope="Public",
        category=category,
        event=event_name,
        urgency=urgency,
        severity=severity,
        certainty=certainty,
        headline=headline,
        description=description,
        instruction=instruction,
        area_desc=area_desc,
        lat=event.lat,
        lon=event.lon,
        radius_km=radius_km,
        xml_payload=xml_payload,
        generated_by=admin_username,
        generated_at=now,
    )

    db.add(alert_model)
    db.commit()
    db.refresh(alert_model)
    return alert_model


def get_cap_alerts(db: Session, limit: int = 100) -> List[CapAlertModel]:
    return db.query(CapAlertModel).order_by(desc(CapAlertModel.generated_at)).limit(limit).all()


def get_cap_alert_by_id(db: Session, alert_id: str) -> Optional[CapAlertModel]:
    return db.query(CapAlertModel).filter(CapAlertModel.id == alert_id).first()


