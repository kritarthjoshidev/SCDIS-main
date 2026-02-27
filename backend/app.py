import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
# Routers
from routes.decision import router as decision_router

logger = logging.getLogger("SCDIS")


# ==========================
# FastAPI App
# ==========================
app = FastAPI(
    title="Smart Campus Decision Intelligence System",
    version="2.0",
    description="AI-powered campus energy decision intelligence backend"
)


# ==========================
# CORS configuration
# ==========================
def _parse_cors_origins(raw: str) -> list[str]:
    origins = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    if not origins:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return origins


CORS_ORIGINS = _parse_cors_origins(settings.CORS_ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================
# Register routers
# ==========================
app.include_router(decision_router)


# ==========================
# Startup event
# ==========================
@app.on_event("startup")
async def startup_log():
    logger.info("SCDIS backend started successfully")


# ==========================
# Health check endpoint
# ==========================
@app.get("/")
def root():
    return {"message": "SCDIS AI backend running"}

from routes.monitoring import router as monitoring_router
app.include_router(monitoring_router)

from routes.orchestrator import router as orchestrator_router
app.include_router(orchestrator_router)

from scheduler import AutonomousScheduler

scheduler = AutonomousScheduler()

@app.on_event("startup")
def start_scheduler():
    scheduler.start()

from routes.admin import router as admin_router
app.include_router(admin_router)

from routes.demo import router as demo_router
app.include_router(demo_router)

from routes.autonomous_ai import router as autonomous_ai_router
app.include_router(autonomous_ai_router)

from routes.telemetry import router as telemetry_router
app.include_router(telemetry_router)
from routes.enterprise_auth import router as enterprise_auth_router
app.include_router(enterprise_auth_router)
from routes.training_data import router as training_data_router
app.include_router(training_data_router)

from core.logging_config import LoggingConfig
LoggingConfig.setup_logging()

from core.enterprise_autonomous_bootstrap import enterprise_autonomous_bootstrap
from services.laptop_runtime_service import laptop_runtime_service
from services.enterprise_identity_service import enterprise_identity_service

@app.on_event("startup")
async def startup_enterprise_bootstrap():
    enterprise_autonomous_bootstrap.start()


@app.on_event("startup")
def start_laptop_runtime():
    laptop_runtime_service.start()


@app.on_event("startup")
def start_auto_training_pipeline():
    enterprise_identity_service.start_auto_trainer(interval_sec=120, min_samples=20, purge_after_train=True)


@app.on_event("startup")
def validate_production_security():
    if str(settings.ENVIRONMENT).strip().lower() != "production":
        return

    if settings.SECRET_KEY.strip() == "" or settings.SECRET_KEY == "dev-only-secret-change-in-production":
        raise RuntimeError("SECRET_KEY must be configured for production")
    if "*" in CORS_ORIGINS:
        raise RuntimeError("CORS_ALLOWED_ORIGINS cannot contain '*' in production")
    if os.getenv("SCDIS_ADMIN_PASSWORD", "admin123") == "admin123":
        raise RuntimeError("Set a non-default SCDIS_ADMIN_PASSWORD in production")
