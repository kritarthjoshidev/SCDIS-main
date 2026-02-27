import logging
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.enterprise_identity_service import enterprise_identity_service

logger = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)


class SecurityManager:
    @staticmethod
    def _permissions_for_role(role: str) -> list[str]:
        normalized_role = str(role or "").strip().lower()
        if normalized_role == "admin":
            return ["decision", "runtime_control", "monitoring", "model_ops", "training"]
        if normalized_role == "org_admin":
            return ["decision", "monitoring", "runtime_control", "model_ops", "training"]
        return []

    def authenticate_token(self, token: str) -> Optional[Dict]:
        if not token:
            return None

        try:
            session = enterprise_identity_service.validate_session(token)
        except PermissionError:
            return None

        role = str(session.get("role") or "")
        return {
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "role": role,
            "organization_id": session.get("organization_id"),
            "organization_name": session.get("organization_name"),
            "permissions": self._permissions_for_role(role),
        }

    async def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    ) -> Dict:
        token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
        user = self.authenticate_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return user

    async def get_current_admin(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    ) -> Dict:
        user = await self.get_current_user(credentials)
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )
        return user

    async def verify_token(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    ) -> Dict:
        return await self.get_current_user(credentials)

    def check_permission(self, user: Dict, permission: str):
        if permission not in user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )


security_manager = SecurityManager()
