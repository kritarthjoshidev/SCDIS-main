"""
Enterprise Identity + Training Data Lifecycle Service.

Now supports:
- Local SQLite fallback
- Managed PostgreSQL (Neon/Supabase) via DATABASE_URL
"""

from __future__ import annotations

import hashlib
import os
import secrets
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from core.config import settings


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _normalize_database_url(database_url: str) -> str:
    normalized = str(database_url or "").strip()
    if not normalized:
        return normalized

    if normalized.startswith("postgres://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgres://") :]
    elif normalized.startswith("postgresql://") and "+psycopg" not in normalized:
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    if normalized.startswith("postgresql+psycopg://") and "sslmode=" not in normalized:
        separator = "&" if "?" in normalized else "?"
        normalized = f"{normalized}{separator}sslmode=require"
    return normalized


class EnterpriseIdentityService:
    def __init__(self, db_path: Optional[Path | str] = None, database_url: Optional[str] = None):
        local_sqlite_path = Path(db_path) if db_path else Path(settings.DATA_DIR) / "enterprise_platform.db"
        local_sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        candidate_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or os.getenv("SUPABASE_DB_URL")
            or os.getenv("NEON_DATABASE_URL")
            or f"sqlite:///{local_sqlite_path.as_posix()}"
        )
        self.database_url = _normalize_database_url(candidate_url)
        self.db_backend = "postgresql" if self.database_url.startswith("postgresql+") else "sqlite"

        engine_kwargs: Dict[str, Any] = {"future": True, "pool_pre_ping": True}
        if self.database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        self.engine: Engine = create_engine(self.database_url, **engine_kwargs)

        self.metadata = MetaData()
        self.organizations = Table(
            "organizations",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(160), nullable=False, unique=True),
            Column("created_at", String(64), nullable=False),
        )
        self.users = Table(
            "users",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("organization_id", Integer, ForeignKey("organizations.id"), nullable=True),
            Column("email", String(200), nullable=False, unique=True),
            Column("password_hash", String(256), nullable=False),
            Column("password_salt", String(64), nullable=False),
            Column("role", String(40), nullable=False),
            Column("is_active", Integer, nullable=False, default=1),
            Column("created_at", String(64), nullable=False),
        )
        self.sessions = Table(
            "sessions",
            self.metadata,
            Column("token", String(255), primary_key=True),
            Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
            Column("created_at", String(64), nullable=False),
            Column("expires_at", String(64), nullable=False),
        )
        self.training_samples = Table(
            "training_samples",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("organization_id", Integer, ForeignKey("organizations.id"), nullable=True),
            Column("model_name", String(40), nullable=False),
            Column("payload_json", Text, nullable=False),
            Column("error_tag", String(160), nullable=True),
            Column("status", String(24), nullable=False, default="pending"),
            Column("created_at", String(64), nullable=False),
            Column("trained_at", String(64), nullable=True),
        )
        self.training_runs = Table(
            "training_runs",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("model_name", String(40), nullable=False),
            Column("sample_count", Integer, nullable=False),
            Column("status", String(24), nullable=False),
            Column("notes", Text, nullable=True),
            Column("started_at", String(64), nullable=False),
            Column("completed_at", String(64), nullable=False),
        )

        self._lock = threading.Lock()
        self._auto_thread: Optional[threading.Thread] = None
        self._auto_running = False
        self._auto_interval_sec = 120
        self._auto_min_samples = 20
        self._auto_purge = True
        self._bootstrap()

    def _bootstrap(self):
        self.metadata.create_all(self.engine)
        self._seed_default_admin()

    @staticmethod
    def _hash_password(password: str, salt_hex: Optional[str] = None) -> Dict[str, str]:
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")

        salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return {"hash": derived.hex(), "salt": salt.hex()}

    def _seed_default_admin(self):
        admin_email = os.getenv("SCDIS_ADMIN_EMAIL", "admin@scdis.local").strip().lower()
        admin_password = os.getenv("SCDIS_ADMIN_PASSWORD", "admin123")

        with self.engine.begin() as conn:
            existing = conn.execute(
                select(self.users.c.id).where(
                    and_(self.users.c.role == "admin", self.users.c.email == admin_email)
                )
            ).first()
            if existing:
                return

            hashed = self._hash_password(admin_password)
            conn.execute(
                insert(self.users).values(
                    organization_id=None,
                    email=admin_email,
                    password_hash=hashed["hash"],
                    password_salt=hashed["salt"],
                    role="admin",
                    is_active=1,
                    created_at=_utc_now(),
                )
            )

    def _verify_password(self, password: str, salt_hex: str, expected_hash: str) -> bool:
        hashed = self._hash_password(password, salt_hex=salt_hex)
        return secrets.compare_digest(hashed["hash"], expected_hash)

    def register_organization(self, name: str, admin_email: str, password: str) -> Dict[str, Any]:
        normalized_name = str(name).strip()
        normalized_email = str(admin_email).strip().lower()
        if not normalized_name:
            raise ValueError("Organization name is required")
        if "@" not in normalized_email:
            raise ValueError("Valid admin email is required")

        hashed = self._hash_password(password)
        with self._lock, self.engine.begin() as conn:
            org_exists = conn.execute(
                select(self.organizations.c.id).where(self.organizations.c.name == normalized_name)
            ).first()
            if org_exists:
                raise ValueError("Organization already exists")

            email_exists = conn.execute(select(self.users.c.id).where(self.users.c.email == normalized_email)).first()
            if email_exists:
                raise ValueError("Email already registered")

            org_result = conn.execute(
                insert(self.organizations).values(name=normalized_name, created_at=_utc_now())
            )
            org_id = int(org_result.inserted_primary_key[0])

            user_result = conn.execute(
                insert(self.users).values(
                    organization_id=org_id,
                    email=normalized_email,
                    password_hash=hashed["hash"],
                    password_salt=hashed["salt"],
                    role="org_admin",
                    is_active=1,
                    created_at=_utc_now(),
                )
            )
            user_id = int(user_result.inserted_primary_key[0])

        session = self.create_session(user_id=user_id, ttl_hours=24)
        return {
            "organization_id": org_id,
            "organization_name": normalized_name,
            "user_id": user_id,
            "email": normalized_email,
            "role": "org_admin",
            "token": session["token"],
            "expires_at": session["expires_at"],
        }

    def login(self, email: str, password: str, required_role: Optional[str] = None) -> Dict[str, Any]:
        normalized_email = str(email).strip().lower()
        stmt = (
            select(
                self.users.c.id.label("user_id"),
                self.users.c.organization_id,
                self.users.c.email,
                self.users.c.password_hash,
                self.users.c.password_salt,
                self.users.c.role,
                self.users.c.is_active,
                self.organizations.c.name.label("organization_name"),
            )
            .select_from(self.users.outerjoin(self.organizations, self.organizations.c.id == self.users.c.organization_id))
            .where(self.users.c.email == normalized_email)
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()

        if row is None:
            raise ValueError("Invalid credentials")
        if int(row["is_active"]) != 1:
            raise ValueError("Account is inactive")
        if required_role and str(row["role"]) != required_role:
            raise PermissionError("Role not allowed for this login endpoint")
        if not self._verify_password(
            password=password,
            salt_hex=str(row["password_salt"]),
            expected_hash=str(row["password_hash"]),
        ):
            raise ValueError("Invalid credentials")

        session = self.create_session(user_id=int(row["user_id"]), ttl_hours=24)
        return {
            "user_id": int(row["user_id"]),
            "organization_id": row["organization_id"],
            "organization_name": row["organization_name"],
            "email": row["email"],
            "role": row["role"],
            "token": session["token"],
            "expires_at": session["expires_at"],
        }

    def create_session(self, user_id: int, ttl_hours: int = 24) -> Dict[str, Any]:
        token = secrets.token_urlsafe(36)
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=max(1, int(ttl_hours)))
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.sessions).values(
                    token=token,
                    user_id=int(user_id),
                    created_at=created_at.isoformat(),
                    expires_at=expires_at.isoformat(),
                )
            )
        return {"token": token, "expires_at": expires_at.isoformat()}

    def revoke_session(self, token: str):
        with self.engine.begin() as conn:
            conn.execute(delete(self.sessions).where(self.sessions.c.token == token))

    def validate_session(self, token: str) -> Dict[str, Any]:
        if not token:
            raise PermissionError("Missing token")

        stmt = (
            select(
                self.sessions.c.token,
                self.sessions.c.expires_at,
                self.users.c.id.label("user_id"),
                self.users.c.email,
                self.users.c.role,
                self.users.c.organization_id,
                self.organizations.c.name.label("organization_name"),
            )
            .select_from(
                self.sessions.join(self.users, self.users.c.id == self.sessions.c.user_id).outerjoin(
                    self.organizations, self.organizations.c.id == self.users.c.organization_id
                )
            )
            .where(self.sessions.c.token == token)
        )

        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()

        if row is None:
            raise PermissionError("Invalid session token")

        expires_at = datetime.fromisoformat(str(row["expires_at"]))
        if expires_at < datetime.utcnow():
            self.revoke_session(token)
            raise PermissionError("Session expired")

        return {
            "user_id": int(row["user_id"]),
            "email": row["email"],
            "role": row["role"],
            "organization_id": row["organization_id"],
            "organization_name": row["organization_name"],
        }

    def list_organizations(self) -> List[Dict[str, Any]]:
        stmt = select(self.organizations.c.id, self.organizations.c.name, self.organizations.c.created_at).order_by(
            self.organizations.c.id.desc()
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def ingest_training_sample(
        self,
        model_name: str,
        payload_json: str,
        organization_id: Optional[int] = None,
        error_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        model_name = str(model_name or "forecast").strip().lower()
        if model_name not in {"forecast", "anomaly", "rl"}:
            raise ValueError("Unsupported model_name. Use forecast|anomaly|rl")

        with self.engine.begin() as conn:
            result = conn.execute(
                insert(self.training_samples).values(
                    organization_id=organization_id,
                    model_name=model_name,
                    payload_json=payload_json,
                    error_tag=error_tag,
                    status="pending",
                    created_at=_utc_now(),
                    trained_at=None,
                )
            )
            sample_id = int(result.inserted_primary_key[0])

        return {
            "id": sample_id,
            "model_name": model_name,
            "organization_id": organization_id,
            "status": "pending",
        }

    def training_stats(self) -> Dict[str, Any]:
        grouped_stmt = (
            select(
                self.training_samples.c.model_name,
                self.training_samples.c.status,
                func.count().label("cnt"),
            )
            .group_by(self.training_samples.c.model_name, self.training_samples.c.status)
            .order_by(self.training_samples.c.model_name.asc(), self.training_samples.c.status.asc())
        )

        with self.engine.connect() as conn:
            grouped_rows = conn.execute(grouped_stmt).mappings().all()
            pending = int(
                conn.execute(
                    select(func.count()).select_from(self.training_samples).where(self.training_samples.c.status == "pending")
                ).scalar_one()
            )
            run_count = int(conn.execute(select(func.count()).select_from(self.training_runs)).scalar_one())
            last_run = conn.execute(select(self.training_runs).order_by(self.training_runs.c.id.desc()).limit(1)).mappings().first()

        return {
            "pending_samples": pending,
            "training_run_count": run_count,
            "auto_trainer_running": self._auto_running,
            "auto_trainer_interval_sec": self._auto_interval_sec,
            "auto_trainer_min_samples": self._auto_min_samples,
            "database_backend": self.db_backend,
            "grouped": [dict(row) for row in grouped_rows],
            "last_run": dict(last_run) if last_run else None,
        }

    def list_training_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        stmt = select(self.training_runs).order_by(self.training_runs.c.id.desc()).limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def run_training_cycle(
        self,
        model_name: Optional[str] = None,
        max_samples: int = 500,
        purge_after_train: bool = True,
    ) -> Dict[str, Any]:
        max_samples = max(1, min(int(max_samples), 5000))
        started_at = _utc_now()
        normalized_model = str(model_name).strip().lower() if model_name else None
        if normalized_model and normalized_model not in {"forecast", "anomaly", "rl"}:
            raise ValueError("Unsupported model_name. Use forecast|anomaly|rl")

        with self._lock, self.engine.begin() as conn:
            select_stmt = (
                select(self.training_samples.c.id)
                .where(self.training_samples.c.status == "pending")
                .order_by(self.training_samples.c.id.asc())
                .limit(max_samples)
            )
            if normalized_model:
                select_stmt = select_stmt.where(self.training_samples.c.model_name == normalized_model)

            ids = [int(row["id"]) for row in conn.execute(select_stmt).mappings().all()]

            if not ids:
                completed_at = _utc_now()
                conn.execute(
                    insert(self.training_runs).values(
                        model_name=normalized_model or "mixed",
                        sample_count=0,
                        status="skipped",
                        notes="No pending training samples",
                        started_at=started_at,
                        completed_at=completed_at,
                    )
                )
                return {
                    "status": "skipped",
                    "sample_count": 0,
                    "model_name": normalized_model or "mixed",
                    "purged_count": 0,
                }

            trained_at = _utc_now()
            conn.execute(
                update(self.training_samples)
                .where(self.training_samples.c.id.in_(ids))
                .values(status="trained", trained_at=trained_at)
            )

            purged_count = 0
            if purge_after_train:
                purge_result = conn.execute(delete(self.training_samples).where(self.training_samples.c.id.in_(ids)))
                purged_count = int(purge_result.rowcount or 0)

            completed_at = _utc_now()
            notes = "Auto train completed and trained samples purged." if purge_after_train else "Auto train completed."
            conn.execute(
                insert(self.training_runs).values(
                    model_name=normalized_model or "mixed",
                    sample_count=len(ids),
                    status="completed",
                    notes=notes,
                    started_at=started_at,
                    completed_at=completed_at,
                )
            )

        return {
            "status": "completed",
            "sample_count": len(ids),
            "model_name": normalized_model or "mixed",
            "purged_count": purged_count,
        }

    def _auto_loop(self):
        while self._auto_running:
            try:
                stats = self.training_stats()
                if int(stats.get("pending_samples", 0)) >= self._auto_min_samples:
                    self.run_training_cycle(model_name=None, max_samples=1000, purge_after_train=self._auto_purge)
            except Exception:
                pass
            time.sleep(self._auto_interval_sec)

    def start_auto_trainer(self, interval_sec: int = 120, min_samples: int = 20, purge_after_train: bool = True):
        self._auto_interval_sec = max(15, min(int(interval_sec), 3600))
        self._auto_min_samples = max(1, min(int(min_samples), 1000))
        self._auto_purge = bool(purge_after_train)

        if self._auto_running:
            return

        self._auto_running = True
        self._auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
        self._auto_thread.start()

    def stop_auto_trainer(self):
        self._auto_running = False


enterprise_identity_service = EnterpriseIdentityService()
