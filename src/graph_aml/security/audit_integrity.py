"""Audit event integrity checks."""

from __future__ import annotations

from typing import cast

import pandas as pd

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import AuditIntegrityError

AUDIT_INTEGRITY_COLUMNS = (
    "security_run_id",
    "check_name",
    "status",
    "issue_count",
    "severity",
    "details",
    "metadata",
)

VALID_AUDIT_STATUSES = {"success", "failed", "failure", "warning", "skipped", "completed", "ok"}


def _config(config: SecurityControlConfig | None) -> SecurityControlConfig:
    return config or SecurityControlConfig()


def _record(
    security_run_id: str | None,
    check_name: str,
    issue_count: int,
    severity: str,
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "security_run_id": security_run_id or "",
        "check_name": check_name,
        "status": "pass" if issue_count == 0 else "fail",
        "issue_count": int(issue_count),
        "severity": severity if issue_count else "info",
        "details": details,
        "metadata": {},
    }


def check_audit_required_columns(
    audit_events: pd.DataFrame,
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> dict[str, object]:
    if not isinstance(audit_events, pd.DataFrame):
        raise AuditIntegrityError("audit_events must be a DataFrame")
    resolved = _config(config)
    missing = sorted(
        set(resolved.audit_integrity.required_columns).difference(audit_events.columns)
    )
    return _record(
        security_run_id,
        "required_columns",
        len(missing),
        "high",
        {"missing_columns": missing},
    )


def check_audit_status_values(
    audit_events: pd.DataFrame,
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> dict[str, object]:
    if not isinstance(audit_events, pd.DataFrame):
        raise AuditIntegrityError("audit_events must be a DataFrame")
    resolved = _config(config)
    if (
        not resolved.audit_integrity.require_success_or_failure_status
        or "status" not in audit_events.columns
    ):
        return _record(security_run_id, "status_values", 0, "info", {"unexpected_statuses": []})
    statuses = set(audit_events["status"].dropna().astype(str).str.lower())
    unexpected = sorted(statuses.difference(VALID_AUDIT_STATUSES))
    return _record(
        security_run_id,
        "status_values",
        len(unexpected),
        "medium",
        {"unexpected_statuses": unexpected},
    )


def check_audit_duplicate_events(
    audit_events: pd.DataFrame,
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> dict[str, object]:
    if not isinstance(audit_events, pd.DataFrame):
        raise AuditIntegrityError("audit_events must be a DataFrame")
    resolved = _config(config)
    columns = [
        column
        for column in resolved.audit_integrity.duplicate_check_columns
        if column in audit_events.columns
    ]
    if not columns or audit_events.empty:
        duplicate_count = 0
    else:
        duplicate_count = int(audit_events.duplicated(subset=columns, keep=False).sum())
    return _record(
        security_run_id,
        "duplicate_events",
        duplicate_count,
        "medium",
        {"duplicate_columns": columns},
    )


def run_audit_integrity_checks(
    audit_events: pd.DataFrame,
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> pd.DataFrame:
    """Run configured audit integrity checks."""

    if not isinstance(audit_events, pd.DataFrame):
        raise AuditIntegrityError("audit_events must be a DataFrame")
    rows = [
        check_audit_required_columns(audit_events, config, security_run_id),
        check_audit_status_values(audit_events, config, security_run_id),
        check_audit_duplicate_events(audit_events, config, security_run_id),
    ]
    return cast("pd.DataFrame", pd.DataFrame(rows, columns=AUDIT_INTEGRITY_COLUMNS))
