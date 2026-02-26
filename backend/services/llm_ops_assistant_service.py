"""
LLM Ops Assistant Service

Lightweight log-analysis and ops assistant used by monitoring endpoints.
Falls back to deterministic heuristic behavior when external LLMs are unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class _EvidenceLine:
    line: int
    text: str
    score: float


class LlmOpsAssistantService:
    def __init__(self, log_dir: Path | str):
        self.log_dir = Path(log_dir)
        self._valid_sources = {"application", "errors"}

    def _source_path(self, source: str) -> Path:
        normalized = str(source).strip().lower()
        if normalized not in self._valid_sources:
            raise ValueError(f"Unsupported log source: {source}")
        path = self.log_dir / f"{normalized}.log"
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {path}")
        return path

    def _read_lines(self, source: str, max_lines: int) -> Tuple[Path, List[str]]:
        path = self._source_path(source)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        max_lines = max(20, min(int(max_lines), 4000))
        return path, lines[-max_lines:]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-z0-9_]+", text.lower())

    @staticmethod
    def _extract_insights(lines: List[str]) -> Dict[str, int]:
        joined = "\n".join(lines).lower()
        return {
            "error_count": joined.count("error"),
            "warning_count": joined.count("warn"),
            "timeout_count": joined.count("timeout"),
            "exception_count": joined.count("exception"),
            "total_lines": len(lines),
        }

    def _rank_evidence(self, query: str, lines: List[str], top_k: int) -> List[_EvidenceLine]:
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            query_tokens = {"system"}

        ranked: List[_EvidenceLine] = []
        for idx, line in enumerate(lines, start=1):
            line_tokens = set(self._tokenize(line))
            overlap = query_tokens.intersection(line_tokens)
            if not overlap:
                continue
            score = len(overlap) / max(1, len(query_tokens))
            ranked.append(_EvidenceLine(line=idx, text=line[:320], score=round(float(score), 3)))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: max(1, min(int(top_k), 12))]

    def query_logs(
        self,
        query: str,
        source: str = "application",
        max_lines: int = 700,
        top_k: int = 8,
    ) -> Dict[str, Any]:
        path, lines = self._read_lines(source, max_lines=max_lines)
        query = str(query or "").strip()
        if not query:
            raise ValueError("Query is required")

        insights = self._extract_insights(lines)
        evidence = self._rank_evidence(query=query, lines=lines, top_k=top_k)

        risk_factors = []
        if insights["error_count"] > 0:
            risk_factors.append(f"{insights['error_count']} error markers")
        if insights["warning_count"] > 0:
            risk_factors.append(f"{insights['warning_count']} warnings")
        if insights["timeout_count"] > 0:
            risk_factors.append(f"{insights['timeout_count']} timeout signals")

        if evidence:
            lead = evidence[0].text
            answer = (
                f"Top correlated signal for '{query}' appears in logs around: \"{lead}\". "
                f"Observed {'; '.join(risk_factors) if risk_factors else 'no major risk markers'}."
            )
        else:
            answer = (
                f"No strong log correlation found for '{query}' in last {len(lines)} lines. "
                "Try broader query terms (grid, failover, cpu, memory, alert)."
            )

        return {
            "query": query,
            "source": source,
            "path": str(path),
            "provider": "heuristic",
            "answer": answer,
            "insights": insights,
            "evidence": [item.__dict__ for item in evidence],
        }

    @staticmethod
    def _risk_level(cpu_percent: float, memory_percent: float, grid_load: float, fault_flag: bool) -> str:
        if fault_flag or grid_load >= 0.9 or cpu_percent >= 92 or memory_percent >= 92:
            return "HIGH"
        if grid_load >= 0.75 or cpu_percent >= 80 or memory_percent >= 82:
            return "MEDIUM"
        return "LOW"

    def summarize_runtime(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        telemetry = payload.get("telemetry", {}) if isinstance(payload, dict) else {}
        industrial = telemetry.get("industrial_metrics", {}) if isinstance(telemetry, dict) else {}
        runtime_health = payload.get("runtime_health", []) if isinstance(payload, dict) else []
        alerts = payload.get("alerts", []) if isinstance(payload, dict) else []
        events = payload.get("events", []) if isinstance(payload, dict) else []

        cpu_percent = float(telemetry.get("cpu_percent", 0.0))
        memory_percent = float(telemetry.get("memory_percent", 0.0))
        grid_load = float(industrial.get("grid_load", min(1.0, max(0.0, cpu_percent / 100.0))))
        fault_flag = bool(industrial.get("fault_flag") or telemetry.get("fault_flag"))

        risk = self._risk_level(cpu_percent, memory_percent, grid_load, fault_flag)
        summary = (
            f"Runtime risk={risk}; CPU={cpu_percent:.1f}% MEM={memory_percent:.1f}% "
            f"GRID={grid_load*100:.1f}% fault={'yes' if fault_flag else 'no'}; "
            f"alerts={len(alerts)} events={len(events)}."
        )

        recommendations: List[str] = []
        if risk == "HIGH":
            recommendations.extend(
                [
                    "Trigger immediate failover readiness check.",
                    "Switch to conservative optimization profile for next cycles.",
                    "Prioritize top critical alerts for operator acknowledgment.",
                ]
            )
        elif risk == "MEDIUM":
            recommendations.extend(
                [
                    "Increase scan frequency for short observation window.",
                    "Review drift and retraining status before next peak period.",
                ]
            )
        else:
            recommendations.append("System stable. Continue autonomous scan cadence.")

        signals = {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "grid_load": round(grid_load, 3),
            "fault_flag": fault_flag,
            "runtime_health_items": len(runtime_health),
            "alerts": len(alerts),
            "events": len(events),
        }

        return {
            "risk_level": risk,
            "summary": summary,
            "recommendations": recommendations,
            "signals": signals,
        }

    def ops_recommendations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        summary = self.summarize_runtime(payload)
        signals = summary["signals"]
        risk = summary["risk_level"]

        recommendations: List[Dict[str, str]] = []

        if signals["fault_flag"]:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": "Activate incident runbook for grid failure",
                    "reason": "Fault flag is active in latest telemetry",
                    "expected_impact": "Reduce recovery time and avoid cascading outages",
                }
            )

        if float(signals["cpu_percent"]) >= 85:
            recommendations.append(
                {
                    "priority": "MEDIUM" if risk != "HIGH" else "HIGH",
                    "action": "Temporarily cap non-critical workloads",
                    "reason": "CPU pressure beyond stable envelope",
                    "expected_impact": "Increase decision stability and protect latency",
                }
            )

        if float(signals["memory_percent"]) >= 82:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "action": "Rotate high-memory processes and monitor leaks",
                    "reason": "Memory headroom is shrinking",
                    "expected_impact": "Lower restart risk during peak cycles",
                }
            )

        if float(signals["grid_load"]) >= 0.8:
            recommendations.append(
                {
                    "priority": "MEDIUM" if risk == "MEDIUM" else "HIGH",
                    "action": "Enable aggressive optimization for high-load window",
                    "reason": "Grid load trending near stress boundary",
                    "expected_impact": "Reduce overload probability and energy spikes",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "priority": "LOW",
                    "action": "Maintain baseline autonomous mode",
                    "reason": "Current runtime telemetry is within normal range",
                    "expected_impact": "Sustained stable operation",
                }
            )

        return {
            "risk_level": risk,
            "recommendations": recommendations,
            "signals": signals,
        }
