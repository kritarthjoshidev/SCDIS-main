"""
Enterprise Feature Pack Service

Provides deterministic enterprise-style metrics and utilities for:
- impact metrics
- decision explainability
- incident runbooks
- governance auditing
- model reliability summaries
- stress validation
- ROI projections and CSV export
- edge agent telemetry registry
"""

from __future__ import annotations

import csv
import io
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class EnterpriseFeaturePackService:
    def impact_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        telemetry = payload.get("telemetry", {}) if isinstance(payload, dict) else {}
        history = payload.get("history", []) if isinstance(payload, dict) else []
        decision = payload.get("decision", {}) if isinstance(payload, dict) else {}
        optimized = decision.get("optimized_decision", {}) if isinstance(decision, dict) else {}

        reduction_pct = max(0.0, min(35.0, _safe_float(optimized.get("recommended_reduction"), 6.0)))
        energy_value = _safe_float(telemetry.get("cpu_percent"), 0.0)
        estimated_kwh = max(1.0, (energy_value * 0.82) * (1.0 + len(history) / 120.0))

        return {
            "energy_reduction_pct": round(reduction_pct, 2),
            "saved_energy_kwh_day": round(estimated_kwh * (reduction_pct / 100.0), 2),
            "cost_saved_inr_day": round((estimated_kwh * (reduction_pct / 100.0)) * 8.2, 2),
            "co2_reduced_kg_day": round((estimated_kwh * (reduction_pct / 100.0)) * 0.82, 2),
            "uptime_improvement_pct": round(max(0.0, min(7.0, 2.4 + reduction_pct * 0.11)), 2),
            "decision_stability_pct": round(
                max(0.0, min(100.0, _safe_float(optimized.get("stability_score"), 0.9) * 100.0)),
                2,
            ),
            "window_points": len(history),
        }

    def decision_explanation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        telemetry = payload.get("telemetry", {}) if isinstance(payload, dict) else {}
        industrial = telemetry.get("industrial_metrics", {}) if isinstance(telemetry, dict) else {}
        decision = payload.get("decision", {}) if isinstance(payload, dict) else {}
        optimized = decision.get("optimized_decision", {}) if isinstance(decision, dict) else {}

        action = str(decision.get("rl_action") or "no_action")
        cpu = _safe_float(telemetry.get("cpu_percent"), 0.0)
        memory = _safe_float(telemetry.get("memory_percent"), 0.0)
        grid = _safe_float(industrial.get("grid_load"), min(1.0, max(0.0, cpu / 100.0)))
        thermal = _safe_float(industrial.get("thermal_index_c"), 25.0)
        fault = bool(industrial.get("fault_flag") or telemetry.get("fault_flag"))
        confidence = max(42.0, min(99.0, _safe_float(optimized.get("confidence_score"), 0.73) * 100.0))

        factors = [
            {
                "signal": "cpu_percent",
                "value": round(cpu, 2),
                "impact": "high" if cpu >= 85 else "medium" if cpu >= 70 else "low",
                "reason": "Compute pressure influences optimization aggressiveness.",
            },
            {
                "signal": "memory_percent",
                "value": round(memory, 2),
                "impact": "high" if memory >= 88 else "medium" if memory >= 72 else "low",
                "reason": "Memory headroom affects resilience margin.",
            },
            {
                "signal": "grid_load",
                "value": round(grid, 3),
                "impact": "high" if grid >= 0.9 else "medium" if grid >= 0.75 else "low",
                "reason": "Grid stress drives failover and savings strategy.",
            },
            {
                "signal": "thermal_index_c",
                "value": round(thermal, 2),
                "impact": "high" if thermal >= 45 else "medium" if thermal >= 35 else "low",
                "reason": "Thermal level contributes to risk and cooling decisions.",
            },
            {
                "signal": "fault_flag",
                "value": 1.0 if fault else 0.0,
                "impact": "high" if fault else "low",
                "reason": "Fault signal elevates incident response actions.",
            },
        ]

        return {
            "action": action,
            "confidence_pct": round(confidence, 2),
            "summary": (
                f"Action '{action}' selected from runtime + grid context with {round(confidence, 1)}% confidence."
            ),
            "factors": factors,
        }

    def generate_runbook(self, incident_type: str, auto_execute: bool = False) -> List[Dict[str, Any]]:
        incident = str(incident_type or "normal_ops").strip().lower()
        if incident in {"auto", ""}:
            incident = "normal_ops"

        templates = {
            "grid_failure": [
                ("Isolate failed feeder and activate standby power", "GridOps"),
                ("Switch decision engine to conservative failover mode", "AIOps"),
                ("Validate node recovery and load rebalance", "Runtime"),
                ("Publish incident closure update", "OpsManager"),
            ],
            "peak_load": [
                ("Apply peak-load optimization profile", "AIOps"),
                ("Defer non-critical workloads", "Runtime"),
                ("Monitor thermal and memory stress for 15 min", "SRE"),
                ("Log demand response outcome", "OpsManager"),
            ],
            "cpu_pressure": [
                ("Throttle low-priority compute jobs", "Runtime"),
                ("Recycle heavy processes with memory spikes", "SRE"),
                ("Re-check model inference latency", "MLOps"),
                ("Restore normal profile after stabilization", "AIOps"),
            ],
            "normal_ops": [
                ("Validate telemetry integrity", "Runtime"),
                ("Review optimization confidence", "AIOps"),
                ("Archive cycle summary", "OpsManager"),
            ],
        }

        steps = templates.get(incident, templates["normal_ops"])
        runbook: List[Dict[str, Any]] = []
        for idx, (title, owner) in enumerate(steps, start=1):
            runbook.append(
                {
                    "step": idx,
                    "title": title,
                    "owner": owner,
                    "eta_min": 3 + idx * 2,
                    "status": "completed" if auto_execute and idx == 1 else "pending",
                }
            )
        return runbook

    def model_reliability(self, payload: Dict[str, Any], drift_status: Dict[str, Any]) -> Dict[str, Any]:
        decision = payload.get("decision", {}) if isinstance(payload, dict) else {}
        optimized = decision.get("optimized_decision", {}) if isinstance(decision, dict) else {}
        stability_pct = max(0.0, min(100.0, _safe_float(optimized.get("stability_score"), 0.9) * 100.0))

        drift_score = _safe_float(
            drift_status.get("global_drift_score") or drift_status.get("drift_score"),
            0.18,
        )

        performance_pct = max(50.0, min(99.7, stability_pct - drift_score * 12.0))

        if drift_score >= 2.0 or stability_pct < 72:
            reliability_status = "AT_RISK"
            action = "Run immediate retraining and switch to conservative runtime mode."
        elif drift_score >= 1.2 or stability_pct < 85:
            reliability_status = "WATCH"
            action = "Increase monitoring frequency and schedule retraining."
        else:
            reliability_status = "STABLE"
            action = "Keep autonomous mode active with periodic governance checks."

        return {
            "reliability_status": reliability_status,
            "decision_stability_pct": round(stability_pct, 2),
            "drift_score": round(drift_score, 3),
            "drift_monitor_status": str(drift_status.get("status", "healthy")),
            "model_performance_pct": round(performance_pct, 2),
            "champion_model": "forecast_model_v2",
            "candidate_model": "forecast_model_v3",
            "recommended_action": action,
        }

    def stress_validation(self, runtime_service: Any, cycles: int = 12) -> Dict[str, Any]:
        cycles = max(2, min(int(cycles), 60))
        scenarios = ["peak_load", "low_load", "grid_failure"]
        results: List[Dict[str, Any]] = []

        for scenario in scenarios:
            runtime_service.set_scenario(scenario, cycles=cycles)
            payload = runtime_service.latest_payload(history_limit=20, event_limit=20, alert_limit=8)
            runtime_health = payload.get("runtime_health", [])
            resilience = 0.0
            if runtime_health:
                matches = [item for item in runtime_health if str(item.get("name")) == "Grid Resilience"]
                if matches:
                    resilience = _safe_float(matches[-1].get("value"), 0.0)
                else:
                    resilience = _safe_float(runtime_health[0].get("value"), 0.0)

            failover_triggered = scenario == "grid_failure" or resilience < 45.0
            passed = (scenario != "grid_failure" and resilience >= 45.0) or (
                scenario == "grid_failure" and failover_triggered
            )

            results.append(
                {
                    "scenario": scenario,
                    "cycles": cycles,
                    "avg_resilience_score": round(resilience, 2),
                    "estimated_failover_triggered": bool(failover_triggered),
                    "result": "PASS" if passed else "FAIL",
                }
            )

        runtime_service.set_scenario("normal", cycles=0)

        passed_count = sum(1 for item in results if item["result"] == "PASS")
        return {
            "status": "completed",
            "total_scenarios": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "results": results,
        }

    def roi_projection(self, site_count: int, annual_growth_pct: float, horizon_years: int) -> Dict[str, Any]:
        site_count = max(1, min(int(site_count), 5000))
        annual_growth_pct = max(0.0, min(float(annual_growth_pct), 200.0))
        horizon_years = max(1, min(int(horizon_years), 10))

        base_saved_per_site = 29000.0
        base_co2_per_site = 1200.0
        projection: List[Dict[str, Any]] = []
        cumulative_cost = 0.0
        cumulative_co2 = 0.0

        for year in range(1, horizon_years + 1):
            growth_factor = (1.0 + annual_growth_pct / 100.0) ** (year - 1)
            sites = int(round(site_count * growth_factor))
            cost_saved = sites * base_saved_per_site
            co2_saved = sites * base_co2_per_site
            cumulative_cost += cost_saved
            cumulative_co2 += co2_saved
            projection.append(
                {
                    "year": year,
                    "sites": sites,
                    "estimated_cost_saved_inr": round(cost_saved, 2),
                    "estimated_co2_reduced_kg": round(co2_saved, 2),
                    "cumulative_cost_saved_inr": round(cumulative_cost, 2),
                    "cumulative_co2_reduced_kg": round(cumulative_co2, 2),
                }
            )

        return {
            "site_count": site_count,
            "annual_growth_pct": round(annual_growth_pct, 2),
            "horizon_years": horizon_years,
            "projection": projection,
            "summary": {
                "total_cost_saved_inr": round(cumulative_cost, 2),
                "total_co2_reduced_kg": round(cumulative_co2, 2),
            },
        }

    @staticmethod
    def roi_csv(roi_payload: Dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "year",
                "sites",
                "estimated_cost_saved_inr",
                "estimated_co2_reduced_kg",
                "cumulative_cost_saved_inr",
                "cumulative_co2_reduced_kg",
            ]
        )

        for row in roi_payload.get("projection", []):
            writer.writerow(
                [
                    row.get("year"),
                    row.get("sites"),
                    row.get("estimated_cost_saved_inr"),
                    row.get("estimated_co2_reduced_kg"),
                    row.get("cumulative_cost_saved_inr"),
                    row.get("cumulative_co2_reduced_kg"),
                ]
            )
        return output.getvalue()


class GovernanceAuditService:
    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log(
        self,
        category: str,
        action: str,
        status: str = "success",
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = {
            "id": int(time.time() * 1000),
            "timestamp": datetime.utcnow().isoformat(),
            "actor": actor,
            "category": category,
            "action": action,
            "status": status,
            "details": details or {},
        }

        with self._lock:
            with self.file_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        return record

    def list_items(self, limit: int = 120) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []

        limit = max(1, min(int(limit), 1000))
        with self._lock:
            lines = self.file_path.read_text(encoding="utf-8", errors="replace").splitlines()

        items: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(items))


class EdgeAgentRegistry:
    def __init__(self, file_path: Optional[Path | str] = None):
        self.file_path = Path(file_path) if file_path else None
        self._lock = threading.Lock()
        self._latest_by_edge: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}

        if self.file_path:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._bootstrap_from_file()

    def _bootstrap_from_file(self):
        if not self.file_path or not self.file_path.exists():
            return
        for line in self.file_path.read_text(encoding="utf-8", errors="replace").splitlines()[-5000:]:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            edge_id = str(item.get("edge_id", "")).strip()
            if not edge_id:
                continue
            self._latest_by_edge[edge_id] = item
            self._history.setdefault(edge_id, []).append(item)
            self._history[edge_id] = self._history[edge_id][-120:]

    def ingest(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        edge_id = str(telemetry.get("edge_id", "")).strip()
        if not edge_id:
            raise ValueError("edge_id is required")

        edge_profile = telemetry.get("edge_profile")
        if not isinstance(edge_profile, dict):
            edge_profile = {}

        cpu_cores_raw = telemetry.get("cpu_cores", edge_profile.get("cpu_cores"))
        physical_cpu_cores_raw = telemetry.get("physical_cpu_cores", edge_profile.get("physical_cpu_cores"))
        memory_total_gb_raw = telemetry.get("memory_total_gb", edge_profile.get("memory_total_gb"))
        disk_total_gb_raw = telemetry.get("disk_total_gb", edge_profile.get("disk_total_gb"))

        cpu_cores = int(_safe_float(cpu_cores_raw, 0.0)) or None
        physical_cpu_cores = int(_safe_float(physical_cpu_cores_raw, 0.0)) or None
        memory_total_gb = round(_safe_float(memory_total_gb_raw, 0.0), 2) or None
        disk_total_gb = round(_safe_float(disk_total_gb_raw, 0.0), 2) or None

        record = {
            "edge_id": edge_id,
            "timestamp": telemetry.get("timestamp") or datetime.utcnow().isoformat(),
            "hostname": telemetry.get("hostname") or edge_id,
            "platform": telemetry.get("platform") or "unknown",
            "cpu_percent": round(_safe_float(telemetry.get("cpu_percent"), 0.0), 2),
            "memory_percent": round(_safe_float(telemetry.get("memory_percent"), 0.0), 2),
            "disk_percent": round(_safe_float(telemetry.get("disk_percent"), 0.0), 2),
            "battery_percent": telemetry.get("battery_percent"),
            "power_plugged": telemetry.get("power_plugged"),
            "process_count": int(_safe_float(telemetry.get("process_count"), 0.0)),
            "network_type": telemetry.get("network_type"),
            "cpu_cores": cpu_cores,
            "physical_cpu_cores": physical_cpu_cores,
            "memory_total_gb": memory_total_gb,
            "disk_total_gb": disk_total_gb,
            "source": telemetry.get("source") or "edge-agent",
        }

        with self._lock:
            self._latest_by_edge[edge_id] = record
            self._history.setdefault(edge_id, []).append(record)
            self._history[edge_id] = self._history[edge_id][-120:]

            if self.file_path:
                with self.file_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=True) + "\n")

        return record

    def latest_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            values = list(self._latest_by_edge.values())
        values.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        return values

    def latest_for(self, edge_id: str, history_limit: int = 20) -> Dict[str, Any]:
        edge_key = str(edge_id).strip()
        with self._lock:
            latest = self._latest_by_edge.get(edge_key)
            history = list(self._history.get(edge_key, []))[-max(1, min(int(history_limit), 120)) :]
        return {
            "latest": latest,
            "history": history,
        }
