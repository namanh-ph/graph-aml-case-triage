"""Summary helpers for security control outputs."""

from __future__ import annotations

import pandas as pd

from graph_aml.security.validation import SecurityControlResult


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {
        str(key): int(value) for key, value in frame[column].value_counts().sort_index().items()
    }


def summarise_sensitive_fields(fields: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(fields)),
        "classification_counts": _counts(fields, "classification"),
        "schema_counts": _counts(fields, "schema_name"),
    }


def summarise_permission_matrix(matrix: pd.DataFrame) -> dict[str, object]:
    allowed_count = int(matrix["allowed"].astype(bool).sum()) if "allowed" in matrix.columns else 0
    return {
        "row_count": int(len(matrix)),
        "role_counts": _counts(matrix, "role"),
        "allowed_action_count": allowed_count,
    }


def summarise_secrets_scan(findings: pd.DataFrame) -> dict[str, object]:
    unallowed = (
        int((~findings["allowed"].astype(bool)).sum())
        if "allowed" in findings.columns and not findings.empty
        else 0
    )
    return {
        "row_count": int(len(findings)),
        "pattern_counts": _counts(findings, "pattern_name"),
        "unallowed_finding_count": unallowed,
        "warning": unallowed > 0,
    }


def summarise_audit_integrity(checks: pd.DataFrame) -> dict[str, object]:
    issues = int(checks["issue_count"].fillna(0).sum()) if "issue_count" in checks.columns else 0
    return {
        "row_count": int(len(checks)),
        "status_counts": _counts(checks, "status"),
        "issue_count": issues,
        "warning": issues > 0,
    }


def security_control_result_to_dict(result: SecurityControlResult) -> dict[str, object]:
    return {
        "security_run_id": result.security_run_id,
        "summary": result.summary,
        "metadata": result.metadata,
        "sensitive_fields": summarise_sensitive_fields(result.sensitive_fields),
        "permission_matrix": summarise_permission_matrix(result.permission_matrix),
        "secrets_scan": summarise_secrets_scan(result.secrets_scan),
        "audit_integrity": summarise_audit_integrity(result.audit_integrity),
    }
