import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd

from core.config import settings
from ai_engine.retraining_engine import RetrainingEngine

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Handles telemetry ingestion, validation, dataset updates,
    and retraining triggers
    """

    REQUIRED_FIELDS = [
        "building_id",
        "temperature",
        "humidity",
        "occupancy",
        "day_of_week",
        "hour",
        "energy_usage_kwh",
    ]

    NUMERIC_BOUNDS = {
        "building_id": (1, 10000),
        "temperature": (-30.0, 70.0),
        "humidity": (0.0, 100.0),
        "occupancy": (0.0, 20000.0),
        "day_of_week": (0, 6),
        "hour": (0, 23),
        "energy_usage_kwh": (0.0, 100000.0),
        "current_load": (0.0, 100.0),
    }

    OUTLIER_FIELDS = [
        "temperature",
        "humidity",
        "occupancy",
        "energy_usage_kwh",
    ]

    def __init__(self):

        self.dataset_path = os.path.join(
            settings.DATA_DIR,
            "training_dataset.csv"
        )

        self.quarantine_path = os.path.join(
            settings.DATA_DIR,
            "telemetry_quarantine.csv"
        )

        self.retraining_engine = RetrainingEngine()

        # ensure data directory exists
        os.makedirs(settings.DATA_DIR, exist_ok=True)

    # ================================
    # Validation
    # ================================
    def _validate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Telemetry payload must be a JSON object")

        missing_fields = [
            field for field in self.REQUIRED_FIELDS if field not in payload
        ]
        if missing_fields:
            raise ValueError(
                f"Missing telemetry fields: {', '.join(missing_fields)}"
            )

        normalized: Dict[str, Any] = dict(payload)
        field_errors: List[str] = []

        for field, bounds in self.NUMERIC_BOUNDS.items():
            if field not in normalized:
                continue

            value = normalized.get(field)
            coerced, error = self._coerce_numeric(field, value)
            if error:
                field_errors.append(error)
                continue

            lower, upper = bounds
            if coerced < lower or coerced > upper:
                field_errors.append(
                    f"{field} out of allowed range [{lower}, {upper}]: {coerced}"
                )
                continue

            if field in {"building_id", "day_of_week", "hour"}:
                normalized[field] = int(coerced)
            else:
                normalized[field] = float(coerced)

        if field_errors:
            raise ValueError(" ; ".join(field_errors))

        if "current_load" not in normalized:
            energy_usage = float(normalized.get("energy_usage_kwh", 0.0))
            normalized["current_load"] = round(
                min(100.0, max(0.0, energy_usage / 10.0)),
                2
            )

        return normalized

    def _coerce_numeric(self, field: str, value: Any) -> Tuple[float, str]:
        try:
            return float(value), ""
        except (TypeError, ValueError):
            return 0.0, f"{field} must be numeric, got {value!r}"

    def _assess_quality(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        penalties = 0
        warnings: List[str] = []
        anomalies: List[str] = []

        recent = self.get_recent_dataset(max_rows=120)
        if recent:
            recent_df = pd.DataFrame(recent)
            penalties += self._apply_spike_detection(payload, recent_df, warnings, anomalies)
            penalties += self._apply_robust_outlier_detection(payload, recent_df, warnings, anomalies)

        if float(payload.get("humidity", 0.0)) > 90.0 and float(payload.get("temperature", 0.0)) > 40.0:
            anomalies.append("High humidity and high temperature observed together")
            penalties += 8

        trust_score = max(0, min(100, 100 - penalties))
        accepted = trust_score >= 60 and not any("critical" in msg.lower() for msg in anomalies)

        return {
            "trust_score": trust_score,
            "accepted": accepted,
            "warnings": warnings,
            "anomalies": anomalies,
        }

    def _apply_spike_detection(
        self,
        payload: Dict[str, Any],
        recent_df: pd.DataFrame,
        warnings: List[str],
        anomalies: List[str],
    ) -> int:
        penalty = 0
        if recent_df.empty:
            return penalty

        latest_row = recent_df.tail(1).to_dict(orient="records")[0]
        spike_rules = {
            "energy_usage_kwh": (3.0, 100.0),
            "occupancy": (3.0, 100.0),
            "temperature": (2.5, 8.0),
            "humidity": (2.5, 15.0),
        }

        for field, (ratio_limit, abs_delta_limit) in spike_rules.items():
            if field not in payload:
                continue

            prev = latest_row.get(field)
            curr = payload.get(field)
            if prev is None or curr is None:
                continue

            try:
                prev_value = float(prev)
                curr_value = float(curr)
            except (TypeError, ValueError):
                continue

            delta = abs(curr_value - prev_value)
            baseline = max(abs(prev_value), 1e-6)
            ratio = (delta / baseline) if baseline else 0.0

            if delta >= abs_delta_limit and ratio >= ratio_limit:
                anomalies.append(
                    f"Potential critical spike in {field}: prev={prev_value:.2f}, curr={curr_value:.2f}"
                )
                penalty += 20
            elif delta >= abs_delta_limit * 0.6 and ratio >= ratio_limit * 0.7:
                warnings.append(
                    f"Unusual jump in {field}: prev={prev_value:.2f}, curr={curr_value:.2f}"
                )
                penalty += 10

        return penalty

    def _apply_robust_outlier_detection(
        self,
        payload: Dict[str, Any],
        recent_df: pd.DataFrame,
        warnings: List[str],
        anomalies: List[str],
    ) -> int:
        penalty = 0

        for field in self.OUTLIER_FIELDS:
            if field not in payload or field not in recent_df.columns:
                continue

            series = pd.to_numeric(recent_df[field], errors="coerce").dropna()
            if len(series) < 20:
                continue

            current = float(payload[field])
            median = float(series.median())
            mad = float((series - median).abs().median())
            robust_std = max(mad * 1.4826, 1e-6)
            robust_z = abs(current - median) / robust_std

            if robust_z >= 7:
                anomalies.append(
                    f"Statistical outlier in {field} (robust-z={robust_z:.2f})"
                )
                penalty += 16
            elif robust_z >= 4.5:
                warnings.append(
                    f"Potential outlier in {field} (robust-z={robust_z:.2f})"
                )
                penalty += 8

        return penalty

    def validate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._validate_payload(payload)
        quality = self._assess_quality(normalized)
        return {
            "payload": normalized,
            "quality": quality,
        }

    # ================================
    # Data normalization
    # ================================
    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload["timestamp"] = datetime.utcnow().isoformat()
        return payload

    # ================================
    # Dataset append
    # ================================
    def _append_to_dataset(self, payload: Dict[str, Any]):

        df = pd.DataFrame([payload])

        if os.path.exists(self.dataset_path):
            df.to_csv(self.dataset_path, mode="a", header=False, index=False)
        else:
            df.to_csv(self.dataset_path, index=False)

    def _append_to_quarantine(
        self,
        payload: Dict[str, Any],
        quality: Dict[str, Any],
    ):
        quarantine_record = dict(payload)
        quarantine_record["quarantined_at"] = datetime.utcnow().isoformat()
        quarantine_record["trust_score"] = quality.get("trust_score")
        quarantine_record["warnings"] = " | ".join(quality.get("warnings", []))
        quarantine_record["anomalies"] = " | ".join(quality.get("anomalies", []))

        df = pd.DataFrame([quarantine_record])
        if os.path.exists(self.quarantine_path):
            df.to_csv(self.quarantine_path, mode="a", header=False, index=False)
        else:
            df.to_csv(self.quarantine_path, index=False)

    # ================================
    # Rolling dataset control
    # ================================
    def _enforce_dataset_limit(self, max_rows=500000):

        if not os.path.exists(self.dataset_path):
            return

        df = pd.read_csv(self.dataset_path)

        if len(df) > max_rows:
            df = df.tail(max_rows)
            df.to_csv(self.dataset_path, index=False)
            logger.info("Dataset trimmed to rolling window")

    # ================================
    # Retraining trigger logic
    # ================================
    def _should_trigger_retraining(self, rows_added):

        # simple policy: retrain every 10k new rows
        return rows_added >= 10000

    # ================================
    # Public ingest function
    # ================================
    def ingest_telemetry(self, payload):

        try:
            validation = self.validate_payload(payload)
            quality = validation["quality"]
            normalized_payload = validation["payload"]

            normalized_payload = self._normalize_payload(normalized_payload)

            if not quality.get("accepted", False):
                self._append_to_quarantine(normalized_payload, quality)
                logger.warning(
                    "Telemetry quarantined (trust_score=%s)",
                    quality.get("trust_score")
                )
                return {
                    "status": "quarantined",
                    "trust_score": quality.get("trust_score"),
                    "warnings": quality.get("warnings", []),
                    "anomalies": quality.get("anomalies", []),
                }

            self._append_to_dataset(normalized_payload)
            self._enforce_dataset_limit()

            logger.info(
                "Telemetry ingested successfully (trust_score=%s)",
                quality.get("trust_score")
            )

            return {
                "status": "ingested",
                "trust_score": quality.get("trust_score"),
                "warnings": quality.get("warnings", []),
                "anomalies": quality.get("anomalies", []),
            }

        except Exception as e:
            logger.error(f"Telemetry ingestion failed: {e}")
            raise

    # ================================
    # Manual retraining trigger
    # ================================
    def trigger_retraining(self):

        logger.info("Manual retraining triggered")
        self.retraining_engine.retrain_models()

        return {"status": "retraining_started"}

    # ================================
    # Retrieve latest telemetry
    # ================================
    def get_latest(self):
        """
        Returns the most recent telemetry record from the rolling dataset.
        If no dataset exists, returns a sensible default telemetry payload.
        """

        try:
            if os.path.exists(self.dataset_path):
                df = pd.read_csv(self.dataset_path)
                if len(df) > 0:
                    latest = df.tail(1).to_dict(orient="records")[0]
                    # ensure timestamp present
                    latest.setdefault("timestamp", datetime.utcnow().isoformat())
                    if "current_load" not in latest:
                        latest["current_load"] = round(
                            min(100.0, max(0.0, float(latest.get("energy_usage_kwh", 0.0)) / 10.0)),
                            2
                        )
                    return latest

            # fallback default
            return {
                "building_id": 1,
                "temperature": 22.0,
                "humidity": 40.0,
                "occupancy": 0.1,
                "day_of_week": datetime.utcnow().weekday(),
                "hour": datetime.utcnow().hour,
                "energy_usage_kwh": 150.0,
                "current_load": 15.0,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to load latest telemetry: {e}")
            return {
                "building_id": 1,
                "temperature": 22.0,
                "humidity": 40.0,
                "occupancy": 0.1,
                "day_of_week": datetime.utcnow().weekday(),
                "hour": datetime.utcnow().hour,
                "energy_usage_kwh": 150.0,
                "current_load": 15.0,
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_recent_dataset(self, max_rows: int = 500):
        """
        Returns a list of recent telemetry records (as dicts). If no dataset
        exists, returns an empty list.
        """

        try:
            if not os.path.exists(self.dataset_path):
                return []

            df = pd.read_csv(self.dataset_path)
            if df.empty:
                return []

            recent = df.tail(max_rows)
            return recent.to_dict(orient="records")

        except Exception:
            logger.exception("Failed to load recent dataset")
            return []

    def get_latest_telemetry(self) -> Dict[str, Any]:
        return self.get_latest()

    def get_latest_metrics(self) -> Dict[str, Any]:
        latest = self.get_latest()
        energy_usage = float(latest.get("energy_usage_kwh", 0.0))
        return {
            "building_id": int(latest.get("building_id", 1)),
            "temperature": float(latest.get("temperature", 22.0)),
            "humidity": float(latest.get("humidity", 40.0)),
            "occupancy": float(latest.get("occupancy", 0.0)),
            "day_of_week": int(latest.get("day_of_week", datetime.utcnow().weekday())),
            "hour": int(latest.get("hour", datetime.utcnow().hour)),
            "energy_usage_kwh": energy_usage,
            "current_load": float(latest.get("current_load", min(100.0, energy_usage / 10.0))),
            "peak_load": float(latest.get("peak_load", max(100.0, energy_usage / 5.0))),
            "state": str(latest.get("state", "normal")),
            "timestamp": latest.get("timestamp", datetime.utcnow().isoformat()),
        }
