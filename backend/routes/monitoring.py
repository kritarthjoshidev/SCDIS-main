"""
Monitoring Routes
Provides system observability, AI health, drift status and performance metrics
"""

import logging
import json
from collections import deque
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from core.config import settings
from core.security import security_manager
from services.data_drift_monitor import DataDriftMonitor
from ai_engine.retraining_engine import RetrainingEngine
from ml_pipeline.model_registry import ModelRegistry
from services.laptop_runtime_service import laptop_runtime_service
from services.telemetry_service import TelemetryService
from services.report_service import ReportService
from services.enterprise_feature_pack_service import (
    EdgeAgentRegistry,
    EnterpriseFeaturePackService,
    GovernanceAuditService,
)
from services.llm_ops_assistant_service import LlmOpsAssistantService
from ai_engine.forecasting_engine import ForecastingEngine
from utils.model_loader import ModelLoader

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(security_manager.get_current_user)],
)

drift_monitor = DataDriftMonitor()
retraining_engine = RetrainingEngine()
model_registry = ModelRegistry()
telemetry_service = TelemetryService()
forecasting_engine = ForecastingEngine()
report_service = ReportService()
feature_pack_service = EnterpriseFeaturePackService()
governance_audit_service = GovernanceAuditService(Path(settings.LOG_DIR) / "governance_audit.jsonl")
edge_agent_registry = EdgeAgentRegistry(Path(settings.LOG_DIR) / "edge_agent_telemetry.jsonl")
llm_ops_assistant = LlmOpsAssistantService(settings.LOG_DIR)

VALID_LOG_SOURCES = {"application", "errors"}
VALID_MODEL_EXPORTS = {"forecast", "anomaly"}
VALID_REPORT_WINDOWS = {"1d", "1w", "1m", "day", "week", "month"}
VALID_REPORT_RESPONSE_FORMATS = {"json", "markdown", "md"}
VALID_REPORT_DOWNLOAD_FORMATS = {"json", "markdown", "md", "pdf"}


def _tail_lines(file_path: Path, line_count: int):
    buffer = deque(maxlen=max(1, line_count))
    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            buffer.append(line.rstrip("\n"))
    return list(buffer)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tail_csv_record_count(file_path: Path, line_count: int = 200) -> int:
    if not file_path.exists():
        return 0

    lines = _tail_lines(file_path, line_count + 2)
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("building_id,"):
            continue
        count += 1
    return count


def _with_client_edge_overlay(payload: Dict[str, Any], edge_id: str) -> Dict[str, Any]:
    normalized_edge_id = str(edge_id or "").strip()
    if not normalized_edge_id:
        return payload

    edge_lookup = edge_agent_registry.latest_for(edge_id=normalized_edge_id, history_limit=1)
    edge_latest = edge_lookup.get("latest")
    if not isinstance(edge_latest, dict):
        return payload

    telemetry = dict(payload.get("telemetry") or {})
    if not telemetry:
        return payload

    edge_profile = dict(telemetry.get("edge_profile") or {})

    if edge_latest.get("cpu_cores") is not None:
        edge_profile["cpu_cores"] = edge_latest.get("cpu_cores")
    if edge_latest.get("physical_cpu_cores") is not None:
        edge_profile["physical_cpu_cores"] = edge_latest.get("physical_cpu_cores")
    if edge_latest.get("memory_total_gb") is not None:
        edge_profile["memory_total_gb"] = edge_latest.get("memory_total_gb")
    if edge_latest.get("disk_total_gb") is not None:
        edge_profile["disk_total_gb"] = edge_latest.get("disk_total_gb")
    if edge_latest.get("network_type") is not None:
        edge_profile["network_type"] = edge_latest.get("network_type")

    edge_profile["source"] = edge_latest.get("source") or "browser_edge_agent"

    if edge_latest.get("hostname"):
        telemetry["hostname"] = edge_latest.get("hostname")
    if edge_latest.get("platform"):
        telemetry["platform"] = edge_latest.get("platform")
    if edge_latest.get("battery_percent") is not None:
        telemetry["battery_percent"] = edge_latest.get("battery_percent")
    if edge_latest.get("power_plugged") is not None:
        telemetry["power_plugged"] = edge_latest.get("power_plugged")

    telemetry["edge_id"] = edge_latest.get("edge_id") or normalized_edge_id
    telemetry["edge_profile"] = edge_profile

    merged_payload = dict(payload)
    merged_payload["telemetry"] = telemetry
    return merged_payload


def _calculate_forecast_accuracy(recent_rows: list[Dict[str, Any]]) -> tuple[float, int]:
    errors = []
    eligible_rows = recent_rows[-72:]

    for row in eligible_rows:
        actual = _safe_float(row.get("energy_usage_kwh"), default=0.0)
        if actual <= 0:
            continue

        try:
            features = {
                "building_id": int(_safe_float(row.get("building_id"), default=1.0)),
                "temperature": _safe_float(row.get("temperature"), default=25.0),
                "humidity": _safe_float(row.get("humidity"), default=45.0),
                "occupancy": _safe_float(row.get("occupancy"), default=0.0),
                "day_of_week": int(_safe_float(row.get("day_of_week"), default=datetime.utcnow().weekday())),
                "hour": int(_safe_float(row.get("hour"), default=datetime.utcnow().hour)),
            }
            forecast = forecasting_engine.predict(features)
            predicted = _safe_float(forecast.get("predicted_energy_usage"), default=actual)
            error = abs(predicted - actual) / max(actual, 1e-6)
            errors.append(min(error, 2.0))
        except Exception:
            continue

    if not errors:
        return 0.0, 0

    mape = mean(errors)
    accuracy = max(0.0, min(99.5, 100.0 - (mape * 100.0)))
    return round(accuracy, 2), len(errors)


# -------------------------------------------------------------
# SYSTEM HEALTH
# -------------------------------------------------------------
@router.get("/system-health")
async def system_health():
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "services": {
                "drift_monitor": "OK",
                "retraining_engine": "OK",
                "model_registry": "OK"
            }
        }
    except Exception as e:
        logger.exception("System health endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# DRIFT STATUS
# -------------------------------------------------------------
@router.get("/data-drift-status")
async def data_drift_status():
    try:
        return drift_monitor.health_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# TRIGGER DRIFT CHECK
# -------------------------------------------------------------
@router.post("/trigger-drift-check")
async def trigger_drift_check(_: Dict[str, Any] = Depends(security_manager.get_current_user)):
    try:
        result = drift_monitor.run_drift_check()
        return {"status": "completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# MODEL PERFORMANCE
# -------------------------------------------------------------
@router.get("/model-performance")
async def model_performance():
    try:
        perf = model_registry.get_latest_model_performance()
        return {"performance": perf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# RETRAINING STATUS
# -------------------------------------------------------------
@router.get("/retraining-status")
async def retraining_status():
    try:
        return retraining_engine.pipeline_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI PIPELINE HEALTH
# -------------------------------------------------------------
@router.get("/ai-pipeline-health")
async def ai_pipeline_health():
    return {
        "forecast_engine": "OK",
        "rl_engine": "OK",
        "optimization_engine": "OK",
        "reward_engine": "OK",
        "timestamp": datetime.utcnow()
    }


# -------------------------------------------------------------
# EXECUTIVE KPI SNAPSHOT
# -------------------------------------------------------------
@router.get("/executive-kpis")
async def executive_kpis():
    """
    Returns decision-impact KPIs for hackathon/demo storytelling.
    """
    try:
        recent_rows = telemetry_service.get_recent_dataset(max_rows=240)
        energy_values = [
            _safe_float(row.get("energy_usage_kwh"), default=0.0)
            for row in recent_rows
            if _safe_float(row.get("energy_usage_kwh"), default=0.0) > 0
        ]

        energy_reduction_percent = 0.0
        cost_optimization_percent = 0.0
        carbon_reduction_kg = 0.0

        if len(energy_values) >= 12:
            midpoint = len(energy_values) // 2
            baseline = mean(energy_values[:midpoint]) if midpoint > 0 else 0.0
            optimized = mean(energy_values[midpoint:]) if midpoint < len(energy_values) else baseline
            if baseline > 0:
                energy_reduction_percent = max(0.0, ((baseline - optimized) / baseline) * 100.0)
                cost_optimization_percent = max(0.0, energy_reduction_percent * 0.82)
                carbon_reduction_kg = max(0.0, (baseline - optimized) * (len(energy_values[midpoint:]) * 0.82))

        forecast_accuracy_percent, forecast_samples = _calculate_forecast_accuracy(recent_rows)

        dataset_window = min(len(recent_rows), 200)
        quarantine_count = _tail_csv_record_count(Path(telemetry_service.quarantine_path), line_count=200)
        filtered_denominator = dataset_window + quarantine_count
        anomaly_filtered_percent = (
            (quarantine_count / filtered_denominator) * 100.0 if filtered_denominator > 0 else 0.0
        )

        live_payload = laptop_runtime_service.latest_payload(history_limit=120, event_limit=120, alert_limit=30)
        events = live_payload.get("events", [])
        scan_events = sum(1 for event in events if "scan_complete" in str(event.get("message", "")))
        automated_decisions_percent = (
            (scan_events / len(events)) * 100.0 if events else 0.0
        )

        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "energy_reduction_percent": round(energy_reduction_percent, 2),
                "cost_optimization_percent": round(cost_optimization_percent, 2),
                "carbon_reduction_kg": round(carbon_reduction_kg, 2),
                "forecast_accuracy_percent": round(forecast_accuracy_percent, 2),
                "anomaly_filtered_percent": round(anomaly_filtered_percent, 2),
                "automated_decisions_percent": round(automated_decisions_percent, 2),
            },
            "sample_sizes": {
                "telemetry_points": len(recent_rows),
                "forecast_samples": forecast_samples,
                "event_samples": len(events),
            },
        }
    except Exception as e:
        logger.exception("Executive KPI generation failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# REPORT GENERATION (1D / 1W / 1M)
# -------------------------------------------------------------
@router.get("/report")
async def monitoring_report(
    window: str = Query(default="1d"),
    format: str = Query(default="json"),
):
    normalized_window = str(window).strip().lower()
    normalized_format = str(format).strip().lower()

    if normalized_window not in VALID_REPORT_WINDOWS:
        raise HTTPException(status_code=400, detail=f"Unsupported report window: {window}")

    if normalized_format not in VALID_REPORT_RESPONSE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported report format: {format}")

    try:
        report = report_service.generate_report(normalized_window)
        if normalized_format in {"markdown", "md"}:
            return {
                "status": "ok",
                "window": normalized_window,
                "format": "markdown",
                "report": report,
                "markdown": report_service.to_markdown(report),
            }
        return {
            "status": "ok",
            "window": normalized_window,
            "format": "json",
            "report": report,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Monitoring report generation failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# REPORT DOWNLOAD
# -------------------------------------------------------------
@router.get("/report/download")
async def monitoring_report_download(
    window: str = Query(default="1d"),
    format: str = Query(default="markdown"),
):
    normalized_window = str(window).strip().lower()
    normalized_format = str(format).strip().lower()

    if normalized_window not in VALID_REPORT_WINDOWS:
        raise HTTPException(status_code=400, detail=f"Unsupported report window: {window}")

    if normalized_format not in VALID_REPORT_DOWNLOAD_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported report format: {format}")

    try:
        report = report_service.generate_report(normalized_window)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        reports_dir = Path(settings.DATA_DIR) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        if normalized_format == "json":
            report_path = reports_dir / f"scdis_report_{normalized_window}_{timestamp}.json"
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            media_type = "application/json"
        elif normalized_format == "pdf":
            report_path = reports_dir / f"scdis_report_{normalized_window}_{timestamp}.pdf"
            report_service.to_pdf(report, report_path)
            media_type = "application/pdf"
        else:
            report_path = reports_dir / f"scdis_report_{normalized_window}_{timestamp}.md"
            report_path.write_text(report_service.to_markdown(report), encoding="utf-8")
            media_type = "text/markdown"

        return FileResponse(
            path=str(report_path),
            media_type=media_type,
            filename=report_path.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Monitoring report download failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# DRIFT HISTORY
# -------------------------------------------------------------
@router.get("/drift-history")
async def drift_history():
    try:
        history = getattr(drift_monitor, "drift_history", [])
        return {"history": history[-50:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# FORCE MODEL REGISTRY REFRESH
# -------------------------------------------------------------
@router.post("/refresh-model-registry")
async def refresh_model_registry(_: Dict[str, Any] = Depends(security_manager.get_current_user)):
    try:
        model_registry.refresh_registry()
        return {"status": "model registry refreshed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# LIVE LAPTOP DASHBOARD PAYLOAD
# -------------------------------------------------------------
@router.get("/laptop/live-dashboard")
async def live_laptop_dashboard():
    try:
        return laptop_runtime_service.latest_payload(history_limit=30, event_limit=30, alert_limit=10)
    except Exception as e:
        logger.exception("Laptop live dashboard failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# LIVE LAPTOP STATUS
# -------------------------------------------------------------
@router.get("/laptop/status")
async def live_laptop_status():
    try:
        return laptop_runtime_service.health_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AUTO APPLY TOGGLE
# -------------------------------------------------------------
@router.post("/laptop/auto-apply")
async def laptop_auto_apply(
    payload: Dict[str, Any],
    _: Dict[str, Any] = Depends(security_manager.get_current_user),
):
    try:
        enabled = bool(payload.get("enabled", True))
        laptop_runtime_service.set_auto_apply(enabled)
        governance_audit_service.log(
            category="runtime_control",
            action="auto_apply_toggle",
            details={"enabled": enabled},
        )
        return {
            "status": "updated",
            "auto_apply_power_profile": enabled,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# RUNTIME MODE (LIVE_EDGE/SIMULATION/HYBRID)
# -------------------------------------------------------------
@router.post("/laptop/mode")
async def laptop_runtime_mode(
    payload: Dict[str, Any],
    _: Dict[str, Any] = Depends(security_manager.get_current_user),
):
    try:
        mode = str(payload.get("mode", "LIVE_EDGE"))
        laptop_runtime_service.set_mode(mode)
        governance_audit_service.log(
            category="runtime_control",
            action="set_runtime_mode",
            details={"mode": mode.upper()},
        )
        return {
            "status": "updated",
            "mode": mode.upper(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# SCENARIO CONTROL
# -------------------------------------------------------------
@router.post("/laptop/scenario")
async def laptop_scenario(
    payload: Dict[str, Any],
    _: Dict[str, Any] = Depends(security_manager.get_current_user),
):
    try:
        scenario = str(payload.get("scenario", "normal"))
        cycles = int(payload.get("cycles", 12))
        laptop_runtime_service.set_scenario(scenario, cycles=cycles)
        governance_audit_service.log(
            category="runtime_control",
            action="set_scenario",
            details={"scenario": scenario.lower(), "cycles": cycles},
        )
        return {
            "status": "updated",
            "scenario": scenario.lower(),
            "cycles": cycles,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI MODELS: MANUAL RETRAIN
# -------------------------------------------------------------
@router.post("/ai-models/retrain")
async def retrain_ai_models(_: Dict[str, Any] = Depends(security_manager.get_current_user)):
    try:
        result = retraining_engine.run_retraining_pipeline()
        governance_audit_service.log(
            category="model_ops",
            action="retrain_model",
            status=str(result.get("status", "completed")).lower(),
            details={"result_keys": sorted(list(result.keys())) if isinstance(result, dict) else []},
        )
        return {
            "status": result.get("status", "completed"),
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception("AI model retraining endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI MODELS: VIEW LOGS
# -------------------------------------------------------------
@router.get("/ai-models/logs")
async def ai_model_logs(
    source: str = Query(default="application"),
    lines: int = Query(default=150, ge=20, le=1000),
):
    normalized_source = str(source).strip().lower()
    if normalized_source not in VALID_LOG_SOURCES:
        raise HTTPException(status_code=400, detail=f"Unsupported log source: {source}")

    log_path = Path(settings.LOG_DIR) / f"{normalized_source}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {log_path}")

    try:
        log_lines = _tail_lines(log_path, lines)
        return {
            "status": "ok",
            "source": normalized_source,
            "path": str(log_path),
            "line_count": len(log_lines),
            "lines": log_lines,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception("AI model log view failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI MODELS: EXPORT WEIGHTS
# -------------------------------------------------------------
@router.get("/ai-models/export-weights")
async def export_ai_model_weights(model: str = Query(default="forecast")):
    normalized_model = str(model).strip().lower()
    if normalized_model not in VALID_MODEL_EXPORTS:
        raise HTTPException(status_code=400, detail=f"Unsupported model export target: {model}")

    if normalized_model == "anomaly":
        ModelLoader.load_anomaly_model()
        model_path = Path(settings.ANOMALY_MODEL_PATH)
    else:
        ModelLoader.load_forecast_model()
        model_path = Path(settings.FORECAST_MODEL_PATH)

    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model file not found: {model_path}")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{normalized_model}_model_weights_{timestamp}{model_path.suffix or '.pkl'}"
    governance_audit_service.log(
        category="model_ops",
        action="export_weights",
        details={"model": normalized_model, "path": str(model_path)},
    )

    return FileResponse(
        path=str(model_path),
        media_type="application/octet-stream",
        filename=filename,
    )


# -------------------------------------------------------------
# AI ASSISTANT: QUERY LOGS
# -------------------------------------------------------------
@router.post("/ai-assistant/query-logs")
async def ai_assistant_query_logs(payload: Dict[str, Any]):
    query = str(payload.get("query", "")).strip()
    source = str(payload.get("source", "application")).strip().lower()
    max_lines = int(payload.get("max_lines", 700))
    top_k = int(payload.get("top_k", 8))

    try:
        result = llm_ops_assistant.query_logs(query=query, source=source, max_lines=max_lines, top_k=top_k)
        governance_audit_service.log(
            category="ai_assistant",
            action="query_logs",
            details={"query": query, "source": source, "top_k": top_k},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("AI assistant log query failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI ASSISTANT: RUNTIME SUMMARY
# -------------------------------------------------------------
@router.get("/ai-assistant/runtime-summary")
async def ai_assistant_runtime_summary():
    try:
        payload = laptop_runtime_service.latest_payload(history_limit=60, event_limit=80, alert_limit=30)
        result = llm_ops_assistant.summarize_runtime(payload)
        governance_audit_service.log(
            category="ai_assistant",
            action="runtime_summary",
            details={"risk_level": result.get("risk_level")},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except Exception as e:
        logger.exception("AI assistant runtime summary failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI ASSISTANT: OPS RECOMMENDATIONS
# -------------------------------------------------------------
@router.get("/ai-assistant/ops-recommendations")
async def ai_assistant_ops_recommendations():
    try:
        payload = laptop_runtime_service.latest_payload(history_limit=60, event_limit=80, alert_limit=30)
        result = llm_ops_assistant.ops_recommendations(payload)
        governance_audit_service.log(
            category="ai_assistant",
            action="ops_recommendations",
            details={"risk_level": result.get("risk_level")},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except Exception as e:
        logger.exception("AI assistant ops recommendations failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: IMPACT METRICS
# -------------------------------------------------------------
@router.get("/impact-metrics")
async def impact_metrics():
    try:
        payload = laptop_runtime_service.latest_payload(history_limit=120, event_limit=60, alert_limit=30)
        metrics = feature_pack_service.impact_metrics(payload)
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
        }
    except Exception as e:
        logger.exception("Impact metrics generation failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: DECISION EXPLAINABILITY
# -------------------------------------------------------------
@router.get("/decision/explain")
async def decision_explain():
    try:
        payload = laptop_runtime_service.latest_payload(history_limit=80, event_limit=40, alert_limit=20)
        explanation = feature_pack_service.decision_explanation(payload)
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "explanation": explanation,
        }
    except Exception as e:
        logger.exception("Decision explainability failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: INCIDENT RUNBOOK
# -------------------------------------------------------------
@router.post("/runbook/generate")
async def runbook_generate(payload: Dict[str, Any]):
    incident_type = str(payload.get("incident_type", "auto"))
    auto_execute = bool(payload.get("auto_execute", False))

    try:
        runbook = feature_pack_service.generate_runbook(incident_type=incident_type, auto_execute=auto_execute)
        governance_audit_service.log(
            category="incident_ops",
            action="generate_runbook",
            details={"incident_type": incident_type, "auto_execute": auto_execute},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_type": incident_type,
            "auto_execute": auto_execute,
            "runbook": runbook,
        }
    except Exception as e:
        logger.exception("Runbook generation failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: GOVERNANCE AUDIT TRAIL
# -------------------------------------------------------------
@router.get("/governance/audit")
async def governance_audit(limit: int = Query(default=120, ge=1, le=1000)):
    try:
        items = governance_audit_service.list_items(limit=limit)
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        logger.exception("Governance audit fetch failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: MODEL RELIABILITY
# -------------------------------------------------------------
@router.get("/model-reliability")
async def model_reliability():
    try:
        payload = laptop_runtime_service.latest_payload(history_limit=120, event_limit=80, alert_limit=30)
        drift_status = drift_monitor.health_status()
        reliability = feature_pack_service.model_reliability(payload=payload, drift_status=drift_status)
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "reliability": reliability,
        }
    except Exception as e:
        logger.exception("Model reliability summary failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: STRESS VALIDATION
# -------------------------------------------------------------
@router.post("/stress-test/run")
async def stress_test_run(
    payload: Dict[str, Any],
    _: Dict[str, Any] = Depends(security_manager.get_current_user),
):
    cycles = int(payload.get("cycles", 12))
    try:
        report = feature_pack_service.stress_validation(runtime_service=laptop_runtime_service, cycles=cycles)
        governance_audit_service.log(
            category="validation",
            action="run_stress_validation",
            details={"cycles": cycles, "passed": report.get("passed"), "failed": report.get("failed")},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "report": report,
        }
    except Exception as e:
        logger.exception("Stress validation failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: ROI PROJECTION
# -------------------------------------------------------------
@router.get("/roi/projection")
async def roi_projection(
    site_count: int = Query(default=100, ge=1, le=5000),
    annual_growth_pct: float = Query(default=12.0, ge=0.0, le=200.0),
    horizon_years: int = Query(default=3, ge=1, le=10),
):
    try:
        roi = feature_pack_service.roi_projection(
            site_count=site_count,
            annual_growth_pct=annual_growth_pct,
            horizon_years=horizon_years,
        )
        governance_audit_service.log(
            category="business_analytics",
            action="roi_projection",
            details={"site_count": site_count, "annual_growth_pct": annual_growth_pct, "horizon_years": horizon_years},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            **roi,
        }
    except Exception as e:
        logger.exception("ROI projection failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: ROI EXPORT CSV
# -------------------------------------------------------------
@router.get("/roi/projection/export")
async def roi_projection_export(
    site_count: int = Query(default=100, ge=1, le=5000),
    annual_growth_pct: float = Query(default=12.0, ge=0.0, le=200.0),
    horizon_years: int = Query(default=3, ge=1, le=10),
):
    try:
        roi = feature_pack_service.roi_projection(
            site_count=site_count,
            annual_growth_pct=annual_growth_pct,
            horizon_years=horizon_years,
        )
        csv_data = feature_pack_service.roi_csv(roi)
        governance_audit_service.log(
            category="business_analytics",
            action="roi_export_csv",
            details={"site_count": site_count, "annual_growth_pct": annual_growth_pct, "horizon_years": horizon_years},
        )
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=roi_projection_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
                )
            },
        )
    except Exception as e:
        logger.exception("ROI CSV export failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: EDGE AGENT INGEST
# -------------------------------------------------------------
@router.post("/edge-agent/ingest")
async def edge_agent_ingest(payload: Dict[str, Any]):
    try:
        telemetry = edge_agent_registry.ingest(payload)
        governance_audit_service.log(
            category="edge_sync",
            action="ingest_edge_telemetry",
            details={"edge_id": telemetry.get("edge_id"), "source": telemetry.get("source")},
        )
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "telemetry": telemetry,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Edge agent ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: EDGE AGENT LATEST (ALL)
# -------------------------------------------------------------
@router.get("/edge-agent/latest")
async def edge_agent_latest():
    try:
        edges = edge_agent_registry.latest_all()
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "edge_count": len(edges),
            "edges": edges,
        }
    except Exception as e:
        logger.exception("Edge latest fetch failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ENTERPRISE: EDGE AGENT LATEST (BY ID)
# -------------------------------------------------------------
@router.get("/edge-agent/latest/{edge_id}")
async def edge_agent_latest_by_id(edge_id: str, history_limit: int = Query(default=20, ge=1, le=120)):
    try:
        result = edge_agent_registry.latest_for(edge_id=edge_id, history_limit=history_limit)
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "edge_id": edge_id,
            "latest": result.get("latest"),
            "history": result.get("history"),
        }
    except Exception as e:
        logger.exception("Edge latest-by-id fetch failed")
        raise HTTPException(status_code=500, detail=str(e))
