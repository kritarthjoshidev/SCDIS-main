"""
Monitoring Report Service

Generates executive infrastructure reports for selectable time windows:
- 1 day
- 1 week
- 1 month
"""

from __future__ import annotations

import logging
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

import pandas as pd

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except Exception:  # pragma: no cover - optional runtime dependency
    matplotlib = None
    plt = None
    PdfPages = None

from core.config import settings
from services.telemetry_service import TelemetryService
from services.laptop_runtime_service import laptop_runtime_service
from ai_engine.forecasting_engine import ForecastingEngine

logger = logging.getLogger(__name__)

# --- Uptime Estimation Constants ---
UPTIME_BASE_RUNNING = 99.92
UPTIME_BASE_STOPPED = 97.50
UPTIME_PENALTY_SCAN_ERROR = 1.75
UPTIME_PENALTY_HIGH_QUARANTINE = 0.35
QUARANTINE_THRESHOLD_FOR_PENALTY = 30
MIN_UPTIME_CLAMP = 90.0
MAX_UPTIME_CLAMP = 99.99
# ------------------------------------


WINDOW_TO_DAYS = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
    "day": 1,
    "week": 7,
    "month": 30,
}


class ReportService:
    def __init__(self):
        self.telemetry_service = TelemetryService()
        self.forecasting_engine = ForecastingEngine()

    def generate_report(self, window: str = "1d") -> Dict[str, Any]:
        days = self._resolve_window_days(window)
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        window_start = now - timedelta(days=days)

        telemetry_rows = self._load_window_rows(window_start, days)
        quarantine_rows = self._load_quarantine_rows(window_start, days)
        live_payload = laptop_runtime_service.latest_payload(history_limit=720, event_limit=250, alert_limit=120)

        summary = self._build_executive_summary(days, telemetry_rows, quarantine_rows, live_payload)
        system_health = self._build_system_health_dashboard(live_payload)
        performance = self._build_performance_section(telemetry_rows, days)
        security = self._build_security_section(live_payload, quarantine_rows)
        recommendations = self._build_recommendations(summary, security, live_payload)

        report_id = f"SCDIS-RPT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{days}D"
        return {
            "report_id": report_id,
            "generated_at": datetime.utcnow().isoformat(),
            "window": f"{days}d",
            "window_label": f"Last {days} Day{'s' if days > 1 else ''}",
            "executive_summary": summary,
            "system_health_dashboard": system_health,
            "performance": performance,
            "security_incidents": security,
            "strategic_recommendations": recommendations,
        }

    def to_markdown(self, report: Dict[str, Any]) -> str:
        summary = report.get("executive_summary", {})
        systems = report.get("system_health_dashboard", [])
        performance = report.get("performance", {})
        security = report.get("security_incidents", {})
        recommendations = report.get("strategic_recommendations", [])

        lines: List[str] = [
            "# University IT Infrastructure & Server Performance Report",
            "",
            f"**Report ID:** {report.get('report_id', 'N/A')}",
            f"**Generated At:** {report.get('generated_at', 'N/A')}",
            f"**Window:** {report.get('window_label', 'N/A')}",
            "",
            "## 1. Executive Summary",
            (
                f"Uptime remained at **{summary.get('uptime_percent', 0):.2f}%**, "
                f"with **{summary.get('records_analyzed', 0)}** telemetry samples analyzed. "
                f"Estimated energy optimized: **{summary.get('energy_optimized_kwh', 0):.2f} kWh**. "
                f"Forecast accuracy: **{summary.get('forecast_accuracy_percent', 0):.2f}%**."
            ),
            "",
            "## 2. System Health Dashboard",
            "",
            "| Server Instance | Role | Status | CPU Load | RAM Usage | Notes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for item in systems:
            status = item.get("status", "unknown")
            emoji = "🟢" if status.lower() == "online" else "🟡" if status.lower() == "warning" else "🔴"
            lines.append(
                f"| **{item.get('instance', '-') }** | {item.get('role', '-')} | "
                f"{emoji} {status.title()} | {item.get('cpu_load_percent', 0):.1f}% | "
                f"{item.get('ram_usage_percent', 0):.1f}% | {item.get('notes', '-')} |"
            )

        lines.extend(
            [
                "",
                "## 3. Performance Graphs (Visual Representation)",
                "",
                "### A. Hourly Demand Pattern (Average Load %)",
            ]
        )

        hourly_profile = performance.get("hourly_load_profile", [])
        if hourly_profile:
            for point in hourly_profile:
                bar_units = max(1, int(float(point.get("avg_load_percent", 0.0)) / 5.0))
                lines.append(f"- {point.get('hour', '00:00')} | {'#' * bar_units} {point.get('avg_load_percent', 0):.1f}%")
        else:
            lines.append("- Insufficient telemetry for hourly profile in selected window.")

        lines.extend(
            [
                "",
                "### B. Resource Allocation Summary",
                f"- **Peak Load Hour:** {performance.get('peak_hour', 'N/A')}",
                f"- **Peak Load:** {performance.get('peak_load_percent', 0):.2f}%",
                f"- **Average Energy Usage:** {performance.get('avg_energy_kwh', 0):.2f} kWh",
                "",
                "## 4. Security Incident Report",
                f"- **Anomaly-filtered Records:** {security.get('anomaly_filtered_records', 0)}",
                f"- **Critical Alerts:** {security.get('critical_alerts', 0)}",
                f"- **Warning Alerts:** {security.get('warning_alerts', 0)}",
                f"- **Notable Events:** {security.get('notable_events_count', 0)}",
                "",
                "## 5. Strategic Recommendations",
            ]
        )

        for idx, recommendation in enumerate(recommendations, start=1):
            lines.append(f"{idx}. {recommendation}")

        return "\n".join(lines)

    def to_pdf(self, report: Dict[str, Any], output_path: Path) -> Path:
        if plt is None or PdfPages is None:
            raise RuntimeError(
                "PDF generation dependency missing: install matplotlib in backend environment."
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary = report.get("executive_summary", {})
        systems = report.get("system_health_dashboard", [])
        performance = report.get("performance", {})
        security = report.get("security_incidents", {})
        recommendations = report.get("strategic_recommendations", [])

        with PdfPages(str(output_path)) as pdf:
            self._render_pdf_cover_page(pdf, report, summary)
            self._render_pdf_system_health_page(pdf, report, systems, summary)
            self._render_pdf_performance_page(pdf, report, performance, security)
            self._render_pdf_security_recommendation_page(pdf, security, recommendations)

        return output_path

    def _render_pdf_cover_page(self, pdf: PdfPages, report: Dict[str, Any], summary: Dict[str, Any]) -> None:
        fig = plt.figure(figsize=(8.27, 11.69), facecolor="#f7fbff")
        fig.text(
            0.08,
            0.95,
            "University IT Infrastructure & Server Performance Report",
            fontsize=17,
            fontweight="bold",
            color="#0a2540",
        )

        fig.text(
            0.08,
            0.91,
            f"Report ID: {report.get('report_id', 'N/A')}    Generated: {report.get('generated_at', 'N/A')}",
            fontsize=9,
            color="#1d4f91",
        )
        fig.text(
            0.08,
            0.885,
            f"Window: {report.get('window_label', 'N/A')}",
            fontsize=10,
            color="#1d4f91",
            fontweight="bold",
        )

        fig.text(0.08, 0.84, "1. Executive Summary", fontsize=13, fontweight="bold", color="#0a2540")

        summary_lines = [
            f"- Uptime: {summary.get('uptime_percent', 0):.2f}%",
            f"- Records analyzed: {summary.get('records_analyzed', 0)}",
            f"- Total energy: {summary.get('total_energy_kwh', 0):.2f} kWh",
            f"- Average load: {summary.get('average_load_percent', 0):.2f}%",
            f"- Energy optimized: {summary.get('energy_optimized_kwh', 0):.2f} kWh",
            f"- Forecast accuracy: {summary.get('forecast_accuracy_percent', 0):.2f}%",
            f"- Alerts (critical/warning): {summary.get('critical_alerts', 0)}/{summary.get('warning_alerts', 0)}",
            f"- Quarantined records: {summary.get('quarantined_records', 0)}",
        ]
        fig.text(0.09, 0.80, "\n".join(summary_lines), fontsize=10, color="#1f2937", va="top", linespacing=1.5)

        kpi_labels = [
            "Uptime %",
            "Forecast Acc %",
            "Avg Load %",
            "Energy Optimized\n(kWh)",
        ]
        kpi_values = [
            float(summary.get("uptime_percent", 0.0)),
            float(summary.get("forecast_accuracy_percent", 0.0)),
            float(summary.get("average_load_percent", 0.0)),
            float(summary.get("energy_optimized_kwh", 0.0)),
        ]
        kpi_max = [100.0, 100.0, 100.0, max(1.0, float(summary.get("total_energy_kwh", 1.0)))]

        ax = fig.add_axes([0.08, 0.42, 0.84, 0.30])
        normalized = [
            min(100.0, (value / max_value) * 100.0 if max_value > 0 else 0.0)
            for value, max_value in zip(kpi_values, kpi_max)
        ]
        colors = ["#2563eb", "#16a34a", "#f59e0b", "#7c3aed"]
        ax.barh(kpi_labels, normalized, color=colors, alpha=0.88)
        ax.set_xlim(0, 100)
        ax.set_xlabel("KPI Score (Normalized %)", color="#334155", fontsize=9)
        ax.set_title("2. Executive KPI Snapshot", fontsize=12, color="#0a2540", pad=10)
        ax.grid(axis="x", linestyle="--", alpha=0.25)
        ax.tick_params(colors="#334155", labelsize=9)

        fig.text(
            0.08,
            0.08,
            "Generated by SCDIS Report Engine | Decision Intelligence + Energy Optimization",
            fontsize=8,
            color="#64748b",
        )

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    def _render_pdf_system_health_page(
        self,
        pdf: PdfPages,
        report: Dict[str, Any],
        systems: List[Dict[str, Any]],
        summary: Dict[str, Any],
    ) -> None:
        fig, axes = plt.subplots(2, 1, figsize=(11.69, 8.27), gridspec_kw={"height_ratios": [1.35, 1.0]})
        fig.patch.set_facecolor("#f8fafc")
        fig.suptitle(
            f"System Health Dashboard | {report.get('window_label', 'Monitoring Window')}",
            fontsize=15,
            fontweight="bold",
            color="#0a2540",
            y=0.98,
        )

        ax_table = axes[0]
        ax_table.axis("off")
        table_rows = []
        for row in systems:
            table_rows.append(
                [
                    str(row.get("instance", "-")),
                    str(row.get("role", "-")),
                    str(row.get("status", "-")).title(),
                    f"{float(row.get('cpu_load_percent', 0.0)):.1f}%",
                    f"{float(row.get('ram_usage_percent', 0.0)):.1f}%",
                    str(row.get("notes", "-")),
                ]
            )

        if not table_rows:
            table_rows = [["N/A", "N/A", "N/A", "0.0%", "0.0%", "No telemetry in selected window"]]

        table = ax_table.table(
            cellText=table_rows,
            colLabels=["Server Instance", "Role", "Status", "CPU Load", "RAM Usage", "Notes"],
            cellLoc="left",
            colLoc="left",
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#dbeafe")
                cell.set_text_props(weight="bold", color="#0f172a")
            else:
                cell.set_facecolor("#ffffff" if row % 2 == 0 else "#f8fafc")

        ax_chart = axes[1]
        categories = ["Critical Alerts", "Warning Alerts", "Quarantined", "Records Analyzed"]
        values = [
            float(summary.get("critical_alerts", 0.0)),
            float(summary.get("warning_alerts", 0.0)),
            float(summary.get("quarantined_records", 0.0)),
            float(summary.get("records_analyzed", 0.0)),
        ]
        colors = ["#dc2626", "#f59e0b", "#7c3aed", "#2563eb"]
        ax_chart.bar(categories, values, color=colors, alpha=0.9)
        ax_chart.set_ylabel("Count", color="#334155", fontsize=9)
        ax_chart.set_title("Operational Risk & Volume Indicators", fontsize=11, color="#0a2540")
        ax_chart.grid(axis="y", linestyle="--", alpha=0.25)
        ax_chart.tick_params(axis="x", labelrotation=15, labelsize=8, colors="#334155")
        ax_chart.tick_params(axis="y", labelsize=8, colors="#334155")

        plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.95])
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    def _render_pdf_performance_page(
        self,
        pdf: PdfPages,
        report: Dict[str, Any],
        performance: Dict[str, Any],
        security: Dict[str, Any],
    ) -> None:
        fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))
        fig.patch.set_facecolor("#f8fafc")
        fig.suptitle(
            f"Performance Analytics & Alert Trends | {report.get('window_label', 'Monitoring Window')}",
            fontsize=15,
            fontweight="bold",
            color="#0a2540",
            y=0.98,
        )

        hourly_profile = performance.get("hourly_load_profile", [])
        hours = [str(point.get("hour", "00:00")) for point in hourly_profile]
        loads = [float(point.get("avg_load_percent", 0.0)) for point in hourly_profile]

        ax1 = axes[0, 0]
        if hours and loads:
            ax1.plot(hours, loads, marker="o", linewidth=2.0, color="#2563eb")
            ax1.fill_between(hours, loads, color="#bfdbfe", alpha=0.35)
        else:
            ax1.plot(["00:00"], [0.0], marker="o", color="#94a3b8")
        ax1.set_title("A. Hourly Demand Pattern (Avg Load %)", fontsize=10, color="#0f172a")
        ax1.set_ylabel("Load %", fontsize=9, color="#334155")
        ax1.grid(linestyle="--", alpha=0.25)
        ax1.tick_params(axis="x", labelrotation=45, labelsize=8)
        ax1.tick_params(axis="y", labelsize=8)

        ax2 = axes[0, 1]
        if hours and loads:
            ax2.bar(hours, loads, color="#16a34a", alpha=0.85)
        else:
            ax2.bar(["00:00"], [0.0], color="#94a3b8", alpha=0.85)
        ax2.set_title("B. Load Distribution by Hour", fontsize=10, color="#0f172a")
        ax2.set_ylabel("Load %", fontsize=9, color="#334155")
        ax2.grid(axis="y", linestyle="--", alpha=0.25)
        ax2.tick_params(axis="x", labelrotation=45, labelsize=8)
        ax2.tick_params(axis="y", labelsize=8)

        ax3 = axes[1, 0]
        pie_labels = ["Critical Alerts", "Warning Alerts", "Healthy Window"]
        critical = float(security.get("critical_alerts", 0.0))
        warning = float(security.get("warning_alerts", 0.0))
        healthy = max(1.0, 100.0 - (critical + warning))
        pie_values = [max(critical, 0.0), max(warning, 0.0), healthy]
        pie_colors = ["#dc2626", "#f59e0b", "#22c55e"]
        ax3.pie(
            pie_values,
            labels=pie_labels,
            autopct="%1.1f%%",
            startangle=140,
            colors=pie_colors,
            textprops={"fontsize": 8},
        )
        ax3.set_title("C. Alert Composition", fontsize=10, color="#0f172a")

        ax4 = axes[1, 1]
        metric_names = ["Peak Load %", "Avg Energy kWh", "Notable Events"]
        metric_values = [
            float(performance.get("peak_load_percent", 0.0)),
            float(performance.get("avg_energy_kwh", 0.0)),
            float(security.get("notable_events_count", 0.0)),
        ]
        ax4.barh(metric_names, metric_values, color=["#7c3aed", "#0ea5e9", "#ef4444"], alpha=0.88)
        ax4.set_title("D. Key Performance Indicators", fontsize=10, color="#0f172a")
        ax4.grid(axis="x", linestyle="--", alpha=0.25)
        ax4.tick_params(axis="x", labelsize=8)
        ax4.tick_params(axis="y", labelsize=8)

        plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.95])
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    def _render_pdf_security_recommendation_page(
        self,
        pdf: PdfPages,
        security: Dict[str, Any],
        recommendations: List[str],
    ) -> None:
        fig = plt.figure(figsize=(8.27, 11.69), facecolor="#f8fafc")
        fig.text(0.08, 0.95, "Security Incident Report & Strategic Recommendations", fontsize=15, fontweight="bold", color="#0a2540")

        fig.text(0.08, 0.90, "4. Security Incident Summary", fontsize=12, fontweight="bold", color="#0f172a")
        security_lines = [
            f"- Anomaly-filtered records: {security.get('anomaly_filtered_records', 0)}",
            f"- Critical alerts: {security.get('critical_alerts', 0)}",
            f"- Warning alerts: {security.get('warning_alerts', 0)}",
            f"- Notable events count: {security.get('notable_events_count', 0)}",
        ]
        fig.text(0.09, 0.86, "\n".join(security_lines), fontsize=10, color="#1f2937", va="top", linespacing=1.55)

        notable_events = security.get("notable_events", []) or []
        fig.text(0.08, 0.72, "Notable Events", fontsize=11, fontweight="bold", color="#0f172a")
        if notable_events:
            wrapped_events = []
            for event in notable_events[:10]:
                wrapped_events.append(f"- {textwrap.fill(str(event), width=85)}")
            fig.text(0.09, 0.69, "\n".join(wrapped_events), fontsize=9, color="#334155", va="top", linespacing=1.45)
        else:
            fig.text(0.09, 0.69, "- No high-severity events detected in selected window.", fontsize=9, color="#334155", va="top")

        fig.text(0.08, 0.41, "5. Strategic Recommendations", fontsize=12, fontweight="bold", color="#0f172a")
        if recommendations:
            wrapped_recommendations = []
            for idx, recommendation in enumerate(recommendations[:8], start=1):
                wrapped_recommendations.append(f"{idx}. {textwrap.fill(str(recommendation), width=88)}")
            fig.text(0.09, 0.38, "\n\n".join(wrapped_recommendations), fontsize=9.5, color="#1f2937", va="top", linespacing=1.45)
        else:
            fig.text(0.09, 0.38, "1. Maintain existing operational policy and continue monitoring.", fontsize=9.5, color="#1f2937", va="top")

        fig.text(
            0.08,
            0.06,
            "SCDIS | Professional Automated Report | For campus operations, risk and sustainability planning",
            fontsize=8,
            color="#64748b",
        )

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    def _resolve_window_days(self, window: str) -> int:
        normalized = str(window).strip().lower()
        if normalized not in WINDOW_TO_DAYS:
            raise ValueError(f"Unsupported window: {window}. Use 1d, 1w or 1m.")
        return WINDOW_TO_DAYS[normalized]

    def _load_window_rows(self, window_start: datetime, days: int) -> List[Dict[str, Any]]:
        path = Path(self.telemetry_service.dataset_path)
        if not path.exists():
            return []

        try:
            df = pd.read_csv(path)
            if df.empty:
                return []

            if "timestamp" in df.columns:
                timestamps = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
                valid = timestamps.notna()
                df = df.loc[valid].copy()
                timestamps = timestamps[valid]
                df = df.loc[timestamps >= window_start]
            else:
                fallback_rows = min(len(df), max(50, days * 240))
                df = df.tail(fallback_rows)

            return df.to_dict(orient="records")
        except Exception:
            logger.exception("Failed to load telemetry rows for report")
            return []

    def _load_quarantine_rows(self, window_start: datetime, days: int) -> List[Dict[str, Any]]:
        path = Path(self.telemetry_service.quarantine_path)
        if not path.exists():
            return []

        try:
            df = pd.read_csv(path)
            if df.empty:
                return []

            ts_col = "quarantined_at" if "quarantined_at" in df.columns else "timestamp"
            if ts_col in df.columns:
                timestamps = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
                valid = timestamps.notna()
                df = df.loc[valid].copy()
                timestamps = timestamps[valid]
                df = df.loc[timestamps >= window_start]
            else:
                fallback_rows = min(len(df), max(25, days * 100))
                df = df.tail(fallback_rows)
            return df.to_dict(orient="records")
        except Exception:
            logger.exception("Failed to load quarantine rows for report")
            return []

    def _build_executive_summary(
        self,
        days: int,
        telemetry_rows: List[Dict[str, Any]],
        quarantine_rows: List[Dict[str, Any]],
        live_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        energy_values = [self._safe_float(row.get("energy_usage_kwh")) for row in telemetry_rows]
        energy_values = [value for value in energy_values if value > 0]

        avg_energy = mean(energy_values) if energy_values else 0.0
        total_energy = sum(energy_values) if energy_values else 0.0

        current_loads = [self._safe_float(row.get("current_load")) for row in telemetry_rows]
        current_loads = [value for value in current_loads if value >= 0]
        avg_load = mean(current_loads) if current_loads else 0.0

        reduced_energy = max(0.0, total_energy * 0.18)
        uptime_percent = self._estimate_uptime(live_payload, quarantine_rows)
        forecast_accuracy = self._estimate_forecast_accuracy(telemetry_rows)

        alerts = live_payload.get("alerts", [])
        critical_alerts = sum(1 for alert in alerts if str(alert.get("severity", "")).lower() == "critical")
        warning_alerts = sum(1 for alert in alerts if str(alert.get("severity", "")).lower() == "warning")

        return {
            "uptime_percent": round(uptime_percent, 2),
            "records_analyzed": len(telemetry_rows),
            "window_days": days,
            "total_energy_kwh": round(total_energy, 2),
            "average_energy_kwh": round(avg_energy, 2),
            "average_load_percent": round(avg_load, 2),
            "energy_optimized_kwh": round(reduced_energy, 2),
            "forecast_accuracy_percent": round(forecast_accuracy, 2),
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "quarantined_records": len(quarantine_rows),
        }

    def _build_system_health_dashboard(self, live_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        telemetry = live_payload.get("telemetry", {})
        service_health = live_payload.get("service_health", {})
        runtime_health = live_payload.get("runtime_health", [])
        decision = live_payload.get("decision", {})

        running = bool(service_health.get("running", False))
        status = "online" if running else "warning"

        cpu = self._safe_float(telemetry.get("cpu_percent"))
        memory = self._safe_float(telemetry.get("memory_percent"))

        decision_stability = 0.0
        for item in runtime_health:
            if str(item.get("name", "")).lower() == "decision stability":
                decision_stability = self._safe_float(item.get("value"))
                break

        # Note: The CPU/RAM for sub-services are *estimates* based on the main
        # edge node's telemetry. These multipliers represent a typical distribution
        # of resources in the simulated environment.
        rows = [
            {
                "instance": str(telemetry.get("hostname", "EDGE-NODE")),
                "role": "Edge Telemetry Runtime",
                "status": status,
                "cpu_load_percent": cpu,
                "ram_usage_percent": memory,
                "notes": telemetry.get("platform", "N/A"),
            },
            {
                "instance": "AI-DECISION-ENGINE",
                "role": "Forecast + Prescriptive Optimization",
                "status": "online" if decision else "warning",
                "cpu_load_percent": max(0.0, min(100.0, cpu * 0.65)),
                "ram_usage_percent": max(0.0, min(100.0, memory * 0.7)),
                "notes": f"Decision stability {decision_stability:.1f}%",
            },
            {
                "instance": "SECURITY-FILTER-LAYER",
                "role": "Telemetry Trust & Anomaly Guard",
                "status": "online",
                "cpu_load_percent": max(0.0, min(100.0, cpu * 0.28)),
                "ram_usage_percent": max(0.0, min(100.0, memory * 0.25)),
                "notes": "Quarantine gate active",
            },
            {
                "instance": "MODEL-RETRAIN-PIPELINE",
                "role": "Model Lifecycle & Retraining",
                "status": "online",
                "cpu_load_percent": max(0.0, min(100.0, cpu * 0.35)),
                "ram_usage_percent": max(0.0, min(100.0, memory * 0.4)),
                "notes": "Automated retraining enabled",
            },
        ]

        return rows

    def _build_performance_section(self, telemetry_rows: List[Dict[str, Any]], days: int) -> Dict[str, Any]:
        if not telemetry_rows:
            return {
                "peak_hour": "N/A",
                "peak_load_percent": 0.0,
                "avg_energy_kwh": 0.0,
                "hourly_load_profile": [],
            }

        df = pd.DataFrame(telemetry_rows)
        if "hour" not in df.columns:
            df["hour"] = datetime.utcnow().hour
        if "current_load" not in df.columns and "energy_usage_kwh" in df.columns:
            df["current_load"] = pd.to_numeric(df["energy_usage_kwh"], errors="coerce") / 10.0

        df["hour"] = pd.to_numeric(df["hour"], errors="coerce").fillna(0).astype(int).clip(0, 23)
        df["current_load"] = pd.to_numeric(df.get("current_load"), errors="coerce").fillna(0.0).clip(0.0, 100.0)
        df["energy_usage_kwh"] = pd.to_numeric(df.get("energy_usage_kwh"), errors="coerce").fillna(0.0)

        grouped = df.groupby("hour", as_index=False).agg(
            avg_load=("current_load", "mean"),
            avg_energy=("energy_usage_kwh", "mean"),
        )
        grouped = grouped.sort_values("hour")

        peak_row = grouped.loc[grouped["avg_load"].idxmax()] if not grouped.empty else None
        peak_hour = f"{int(peak_row['hour']):02d}:00" if peak_row is not None else "N/A"
        peak_load = float(peak_row["avg_load"]) if peak_row is not None else 0.0

        profile = [
            {
                "hour": f"{int(row.hour):02d}:00",
                "avg_load_percent": round(float(row.avg_load), 2),
            }
            for row in grouped.itertuples()
        ]

        if days <= 1:
            profile = profile
        elif days <= 7:
            profile = profile[::2]
        else:
            profile = profile[::3]

        return {
            "peak_hour": peak_hour,
            "peak_load_percent": round(peak_load, 2),
            "avg_energy_kwh": round(float(df["energy_usage_kwh"].mean()), 2),
            "hourly_load_profile": profile,
        }

    def _build_security_section(self, live_payload: Dict[str, Any], quarantine_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        alerts = live_payload.get("alerts", [])
        events = live_payload.get("events", [])

        critical_alerts = [alert for alert in alerts if str(alert.get("severity", "")).lower() == "critical"]
        warning_alerts = [alert for alert in alerts if str(alert.get("severity", "")).lower() == "warning"]

        notable_events = [
            str(event.get("message", ""))
            for event in events
            if any(token in str(event.get("message", "")).lower() for token in ("critical", "failure", "anomaly", "error"))
        ]

        return {
            "anomaly_filtered_records": len(quarantine_rows),
            "critical_alerts": len(critical_alerts),
            "warning_alerts": len(warning_alerts),
            "notable_events_count": len(notable_events),
            "notable_events": notable_events[:8],
        }

    def _build_recommendations(
        self,
        summary: Dict[str, Any],
        security: Dict[str, Any],
        live_payload: Dict[str, Any],
    ) -> List[str]:
        recommendations: List[str] = []

        average_load = self._safe_float(summary.get("average_load_percent"))
        quarantined = int(summary.get("quarantined_records", 0))
        forecast_accuracy = self._safe_float(summary.get("forecast_accuracy_percent"))
        critical_alerts = int(security.get("critical_alerts", 0))

        if average_load >= 78:
            recommendations.append("Sustained load is high. Consider adding an edge optimization node to handle peak hours.")
        else:
            recommendations.append("System load is within safe limits. Maintain current configuration and continue hourly monitoring.")

        if quarantined >= 10:
            recommendations.append(
                "High number of quarantined records suggests data quality issues. Check sensor calibration and review noisy telemetry sources."
            )
        else:
            recommendations.append(
                "Telemetry quality is stable; keep current anomaly filtering policy and weekly audits."
            )

        if forecast_accuracy < 85:
            recommendations.append("Forecast accuracy is below target. Retrain the model with a larger dataset before the next peak load period.")
        else:
            recommendations.append("Forecasting model is performing well. Schedule daily incremental retraining to keep it up-to-date.")

        if critical_alerts > 0:
            recommendations.append("Critical alerts require attention. Analyze them and create automated runbooks for common problems.")
        else:
            recommendations.append("System is stable with no critical alerts. Continue proactive health checks.")

        service_health = live_payload.get("service_health", {})
        if service_health.get("last_scan_error"):
            recommendations.append(
                "A telemetry collection error occurred. Investigate the cause and improve the service's error handling (e.g., with retries)."
            )

        return recommendations[:5]

    def _estimate_uptime(self, live_payload: Dict[str, Any], quarantine_rows: List[Dict[str, Any]]) -> float:
        service_health = live_payload.get("service_health", {})
        running = bool(service_health.get("running", False))
        has_scan_error = bool(service_health.get("last_scan_error"))

        base = UPTIME_BASE_RUNNING if running else UPTIME_BASE_STOPPED
        if has_scan_error:
            base -= UPTIME_PENALTY_SCAN_ERROR
        if len(quarantine_rows) > QUARANTINE_THRESHOLD_FOR_PENALTY:
            base -= UPTIME_PENALTY_HIGH_QUARANTINE

        return max(MIN_UPTIME_CLAMP, min(MAX_UPTIME_CLAMP, base))

    def _estimate_forecast_accuracy(self, telemetry_rows: List[Dict[str, Any]]) -> float:
        errors: List[float] = []
        for row in telemetry_rows[-120:]:
            actual = self._safe_float(row.get("energy_usage_kwh"))
            if actual <= 0:
                continue

            try:
                features = {
                    "building_id": int(self._safe_float(row.get("building_id"), 1.0)),
                    "temperature": self._safe_float(row.get("temperature"), 25.0),
                    "humidity": self._safe_float(row.get("humidity"), 45.0),
                    "occupancy": self._safe_float(row.get("occupancy"), 0.0),
                    "day_of_week": int(self._safe_float(row.get("day_of_week"), datetime.utcnow().weekday())),
                    "hour": int(self._safe_float(row.get("hour"), datetime.utcnow().hour)),
                }
                forecast = self.forecasting_engine.predict(features)
                predicted = self._safe_float(forecast.get("predicted_energy_usage"), actual)
                error = abs(predicted - actual) / max(actual, 1e-6)
                errors.append(min(error, 2.0))
            except Exception:
                continue

        if not errors:
            return 0.0
        mape = mean(errors)
        return max(0.0, min(99.5, 100.0 - (mape * 100.0)))

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
