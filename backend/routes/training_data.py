from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from services.enterprise_identity_service import enterprise_identity_service

router = APIRouter(prefix="/training-data", tags=["Training Data"])
bearer = HTTPBearer(auto_error=False)


class TrainingSampleRequest(BaseModel):
    model_name: str = Field(default="forecast", pattern="^(forecast|anomaly|rl)$")
    payload: Dict[str, Any]
    error_tag: Optional[str] = Field(default=None, max_length=120)


class RunTrainingRequest(BaseModel):
    model_name: Optional[str] = Field(default=None)
    max_samples: int = Field(default=500, ge=1, le=5000)
    purge_after_train: bool = True


class AutoTrainerRequest(BaseModel):
    interval_sec: int = Field(default=120, ge=15, le=3600)
    min_samples: int = Field(default=20, ge=1, le=1000)
    purge_after_train: bool = True


def _session_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return enterprise_identity_service.validate_session(credentials.credentials)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _operator_session(session: Dict[str, Any] = Depends(_session_from_credentials)) -> Dict[str, Any]:
    if str(session.get("role")) not in {"admin", "org_admin"}:
        raise HTTPException(status_code=403, detail="Operator access required")
    return session


@router.post("/ingest")
def ingest_training_sample(
    payload: TrainingSampleRequest,
    session: Dict[str, Any] = Depends(_session_from_credentials),
):
    org_id = session.get("organization_id")
    try:
        result = enterprise_identity_service.ingest_training_sample(
            model_name=payload.model_name,
            payload_json=json.dumps(payload.payload, ensure_ascii=True),
            organization_id=org_id,
            error_tag=payload.error_tag,
        )
        return {
            "status": "queued",
            "timestamp": datetime.utcnow().isoformat(),
            "queued_by": session.get("email"),
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-now")
def run_training_now(
    payload: RunTrainingRequest,
    _: Dict[str, Any] = Depends(_operator_session),
):
    try:
        result = enterprise_identity_service.run_training_cycle(
            model_name=payload.model_name,
            max_samples=payload.max_samples,
            purge_after_train=payload.purge_after_train,
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def training_stats(_: Dict[str, Any] = Depends(_operator_session)):
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": enterprise_identity_service.training_stats(),
    }


@router.get("/runs")
def training_runs(
    limit: int = Query(default=30, ge=1, le=200),
    _: Dict[str, Any] = Depends(_operator_session),
):
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "items": enterprise_identity_service.list_training_runs(limit=limit),
    }


@router.post("/auto-trainer/start")
def start_auto_trainer(
    payload: AutoTrainerRequest,
    _: Dict[str, Any] = Depends(_operator_session),
):
    enterprise_identity_service.start_auto_trainer(
        interval_sec=payload.interval_sec,
        min_samples=payload.min_samples,
        purge_after_train=payload.purge_after_train,
    )
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Auto trainer started",
    }


@router.post("/auto-trainer/stop")
def stop_auto_trainer(_: Dict[str, Any] = Depends(_operator_session)):
    enterprise_identity_service.stop_auto_trainer()
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Auto trainer stopped",
    }
