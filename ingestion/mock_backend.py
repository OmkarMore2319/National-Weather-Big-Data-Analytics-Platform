#!/usr/bin/env python3
"""
mock_backend.py - Lightweight Local Mock Backend Receiver for Ingestion Testing

This server runs locally on http://localhost:8000 and mocks the backend's
POST /api/v1/ingest/internal endpoint so you can test live HTTP ingestion
without waiting for Person 1's backend service.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime, timezone
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [MockBackend] %(message)s")
logger = logging.getLogger("MockBackend")

app = FastAPI(title="Mock Weather Backend (PS 26069)")

received_events = []

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Mock Weather Backend Receiver",
        "receivedCount": len(received_events)
    }

@app.post("/api/v1/ingest/internal")
async def ingest_internal(request: Request):
    payload = await request.json()
    received_events.append(payload)

    source = payload.get("source", "OFFICIAL_STATION" if "condition" in payload else "UNKNOWN")
    city = payload.get("city", "Unknown City")
    
    logger.info(f"Received #{len(received_events)} from [{source}] for {city}")

    # Echo back a WeatherEvent-shaped confirmation
    return JSONResponse(
        status_code=201,
        content={
            "id": payload.get("id", str(uuid.uuid4())),
            "status": "ACCEPTED",
            "source": source,
            "city": city,
            "ingestedAt": datetime.now(timezone.utc).isoformat(),
            "payloadEcho": payload
        }
    )

@app.get("/api/v1/events")
def get_events():
    return {"total": len(received_events), "events": received_events[-20:]}

if __name__ == "__main__":
    logger.info("Starting Mock Backend on http://localhost:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
