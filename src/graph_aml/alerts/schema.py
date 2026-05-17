"""Typed AML alert records and schema constants."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from graph_aml.alerts.exceptions import AlertValidationError

ALERT_SEVERITIES = ("low", "medium", "high", "critical")
ALERT_STATUSES = (
    "New",
    "In review",
    "Escalated",
    "Information requested",
    "Closed false positive",
    "Closed suspicious",
    "Archived",
)
ALERT_SOURCES = ("rule", "model", "graph", "manual")

ALERT_COLUMNS = (
    "alert_id",
    "account_id",
    "customer_id",
    "rule_name",
    "typology",
    "severity",
    "risk_score_rule",
    "reason_code",
    "evidence_ids",
    "detection_window_start",
    "detection_window_end",
    "model_run_id",
    "alert_status",
    "created_at",
    "updated_at",
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _required_string(value: object, field_name: str) -> str:
    if _is_missing(value):
        raise AlertValidationError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise AlertValidationError(f"{field_name} is required")
    return text


def _optional_string(value: object) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    return None if not text else text


def _normalise_timestamp(value: object, field_name: str) -> str | None:
    if _is_missing(value):
        return None
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise AlertValidationError(f"{field_name} must be a parseable timestamp")
    return str(pd.Timestamp(timestamp).isoformat())


def _normalise_evidence_ids(values: tuple[str, ...] | list[str] | object) -> tuple[str, ...]:
    if isinstance(values, str):
        stripped = values.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            raw_values: list[object] = [item for item in stripped[1:-1].split(",") if item]
        else:
            raw_values = [stripped]
    elif isinstance(values, tuple | list):
        raw_values = list(values)
    elif _is_missing(values):
        raw_values = []
    elif isinstance(values, Iterable):
        raw_values = list(values)
    else:
        raw_values = [values]

    evidence_ids = tuple(str(value).strip() for value in raw_values if str(value).strip())
    if not evidence_ids:
        raise AlertValidationError("evidence_ids must contain at least one evidence ID")
    return evidence_ids


@dataclass(frozen=True)
class AlertRecord:
    """Standard AML alert record emitted by rule, model, graph, or manual sources."""

    alert_id: str
    account_id: str
    customer_id: str | None
    rule_name: str
    typology: str
    severity: str
    risk_score_rule: float
    reason_code: str
    evidence_ids: tuple[str, ...]
    detection_window_start: str | None
    detection_window_end: str | None
    model_run_id: str | None = None
    alert_status: str = "New"
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        alert_id = _required_string(self.alert_id, "alert_id")
        account_id = _required_string(self.account_id, "account_id")
        rule_name = _required_string(self.rule_name, "rule_name")
        typology = _required_string(self.typology, "typology")
        reason_code = _required_string(self.reason_code, "reason_code")
        severity = _required_string(self.severity, "severity").lower()
        if severity not in ALERT_SEVERITIES:
            raise AlertValidationError(f"severity must be one of {ALERT_SEVERITIES}")
        if self.alert_status not in ALERT_STATUSES:
            raise AlertValidationError(f"alert_status must be one of {ALERT_STATUSES}")

        try:
            risk_score_rule = float(self.risk_score_rule)
        except (TypeError, ValueError) as exc:
            raise AlertValidationError("risk_score_rule must be numeric") from exc
        if risk_score_rule < 0 or risk_score_rule > 100:
            raise AlertValidationError("risk_score_rule must be between 0 and 100")

        evidence_ids = _normalise_evidence_ids(self.evidence_ids)
        detection_window_start = _normalise_timestamp(
            self.detection_window_start,
            "detection_window_start",
        )
        detection_window_end = _normalise_timestamp(
            self.detection_window_end,
            "detection_window_end",
        )
        if detection_window_start is not None and detection_window_end is not None:
            if pd.Timestamp(detection_window_start) > pd.Timestamp(detection_window_end):
                raise AlertValidationError(
                    "detection_window_start must be less than or equal to detection_window_end"
                )

        created_at = _normalise_timestamp(self.created_at, "created_at") or _utc_now_iso()
        updated_at = _normalise_timestamp(self.updated_at, "updated_at") or _utc_now_iso()

        object.__setattr__(self, "alert_id", alert_id)
        object.__setattr__(self, "account_id", account_id)
        object.__setattr__(self, "customer_id", _optional_string(self.customer_id))
        object.__setattr__(self, "rule_name", rule_name)
        object.__setattr__(self, "typology", typology)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "risk_score_rule", risk_score_rule)
        object.__setattr__(self, "reason_code", reason_code)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "detection_window_start", detection_window_start)
        object.__setattr__(self, "detection_window_end", detection_window_end)
        object.__setattr__(self, "model_run_id", _optional_string(self.model_run_id))
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)


def create_alert_record(
    alert_id: str,
    account_id: str,
    customer_id: str | None,
    rule_name: str,
    typology: str,
    severity: str,
    risk_score_rule: float,
    reason_code: str,
    evidence_ids: tuple[str, ...] | list[str],
    detection_window_start: str | None,
    detection_window_end: str | None,
    model_run_id: str | None = None,
    alert_status: str = "New",
) -> AlertRecord:
    """Create and validate a standard alert record."""

    return AlertRecord(
        alert_id=alert_id,
        account_id=account_id,
        customer_id=customer_id,
        rule_name=rule_name,
        typology=typology,
        severity=severity,
        risk_score_rule=risk_score_rule,
        reason_code=reason_code,
        evidence_ids=tuple(evidence_ids),
        detection_window_start=detection_window_start,
        detection_window_end=detection_window_end,
        model_run_id=model_run_id,
        alert_status=alert_status,
    )


def alert_record_to_dict(alert: AlertRecord) -> dict[str, object]:
    """Return a JSON-serialisable alert dictionary."""

    return {
        "alert_id": alert.alert_id,
        "account_id": alert.account_id,
        "customer_id": alert.customer_id,
        "rule_name": alert.rule_name,
        "typology": alert.typology,
        "severity": alert.severity,
        "risk_score_rule": alert.risk_score_rule,
        "reason_code": alert.reason_code,
        "evidence_ids": list(alert.evidence_ids),
        "detection_window_start": alert.detection_window_start,
        "detection_window_end": alert.detection_window_end,
        "model_run_id": alert.model_run_id,
        "alert_status": alert.alert_status,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
    }


def alert_record_from_dict(payload: dict[str, object]) -> AlertRecord:
    """Build a validated alert record from a dictionary payload."""

    try:
        return AlertRecord(
            alert_id=str(payload.get("alert_id", "")),
            account_id=str(payload.get("account_id", "")),
            customer_id=_optional_string(payload.get("customer_id")),
            rule_name=str(payload.get("rule_name", "")),
            typology=str(payload.get("typology", "")),
            severity=str(payload.get("severity", "")),
            risk_score_rule=float(str(payload.get("risk_score_rule", 0))),
            reason_code=str(payload.get("reason_code", "")),
            evidence_ids=_normalise_evidence_ids(payload.get("evidence_ids")),
            detection_window_start=_optional_string(payload.get("detection_window_start")),
            detection_window_end=_optional_string(payload.get("detection_window_end")),
            model_run_id=_optional_string(payload.get("model_run_id")),
            alert_status=str(payload.get("alert_status", "New")),
            created_at=_optional_string(payload.get("created_at")),
            updated_at=_optional_string(payload.get("updated_at")),
        )
    except AlertValidationError:
        raise
    except Exception as exc:
        raise AlertValidationError(f"Invalid alert payload: {exc}") from exc
