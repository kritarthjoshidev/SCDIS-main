from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from services.enterprise_identity_service import enterprise_identity_service

router = APIRouter(prefix="/enterprise/auth", tags=["Enterprise Auth"])
bearer = HTTPBearer(auto_error=False)


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    admin_email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=6, max_length=128)


def _session_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return enterprise_identity_service.validate_session(credentials.credentials)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _admin_session(session: Dict[str, Any] = Depends(_session_from_credentials)) -> Dict[str, Any]:
    if str(session.get("role")) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return session


@router.post("/register-organization")
def register_organization(payload: RegisterOrganizationRequest):
    try:
        result = enterprise_identity_service.register_organization(
            name=payload.organization_name,
            admin_email=payload.admin_email,
            password=payload.password,
        )
        return {
            "status": "created",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login-admin")
def login_admin(payload: LoginRequest):
    try:
        result = enterprise_identity_service.login(
            email=payload.email,
            password=payload.password,
            required_role="admin",
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login-org")
def login_org(payload: LoginRequest):
    try:
        result = enterprise_identity_service.login(
            email=payload.email,
            password=payload.password,
            required_role="org_admin",
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def me(session: Dict[str, Any] = Depends(_session_from_credentials)):
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "session": session,
    }


@router.post("/logout")
def logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    enterprise_identity_service.revoke_session(credentials.credentials)
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/organizations")
def organizations(_: Dict[str, Any] = Depends(_admin_session)):
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "items": enterprise_identity_service.list_organizations(),
    }
