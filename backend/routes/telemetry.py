"""
Telemetry Routes
Provides trusted telemetry ingestion and validation endpoints.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from core.security import security_manager
from services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
    dependencies=[Depends(security_manager.get_current_user)],
)
telemetry_service = TelemetryService()


@router.post("/assess")
async def assess_telemetry(payload: Dict[str, Any]):
    """
    Validate payload and return quality report without persisting data.
    """
    try:
        return telemetry_service.validate_payload(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Telemetry assessment failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_telemetry(payload: Dict[str, Any]):
    """
    Validate + filter telemetry, then either ingest or quarantine.
    """
    try:
        result = telemetry_service.ingest_telemetry(payload)
        if result.get("status") == "quarantined":
            return {
                "status": "quarantined",
                "result": result,
            }
        return {
            "status": "ingested",
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Telemetry ingestion endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def latest_telemetry():
    try:
        return {
            "status": "ok",
            "data": telemetry_service.get_latest(),
        }
    except Exception as e:
        logger.exception("Latest telemetry endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def recent_telemetry(limit: int = Query(default=100, ge=1, le=1000)):
    try:
        return {
            "status": "ok",
            "count": limit,
            "data": telemetry_service.get_recent_dataset(max_rows=limit),
        }
    except Exception as e:
        logger.exception("Recent telemetry endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))
