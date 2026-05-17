"""Security control workflow and validation helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import pandas as pd

from graph_aml.security.audit_integrity import AUDIT_INTEGRITY_COLUMNS, run_audit_integrity_checks
from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import SecurityControlError, SecurityPersistenceError
from graph_aml.security.permissions import PERMISSION_CHECK_COLUMNS, build_permission_matrix
from graph_aml.security.secrets_scan import SECRETS_SCAN_COLUMNS, run_secrets_scan
from graph_aml.security.sensitive_fields import (
    SENSITIVE_FIELD_COLUMNS,
    build_sensitive_field_inventory,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from graph_aml.security.persistence import (
        SecurityControlPersistenceConfig,
        SecurityControlPersistenceResult,
    )


@dataclass(frozen=True)
class SecurityControlResult:
    security_run_id: str
    sensitive_fields: pd.DataFrame
    permission_matrix: pd.DataFrame
    secrets_scan: pd.DataFrame
    audit_integrity: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def build_security_run_id(
    config: SecurityControlConfig | None = None,
    generated_at: pd.Timestamp | None = None,
) -> str:
    """Build a deterministic security run ID for a timestamp and config."""

    resolved = config or SecurityControlConfig()
    timestamp = (generated_at or pd.Timestamp.utcnow()).isoformat()
    digest = hashlib.sha256(
        f"{resolved.security_name}|{resolved.security_version}|{timestamp}".encode()
    ).hexdigest()[:12]
    return (
        f"{resolved.security_version}_{pd.Timestamp(timestamp).strftime('%Y%m%d%H%M%S')}_{digest}"
    )


def validate_security_control_result(result: SecurityControlResult) -> None:
    """Validate required output columns and run ID consistency."""

    if not result.security_run_id:
        raise SecurityControlError("security_run_id must be non-empty")
    expected = (
        (result.sensitive_fields, SENSITIVE_FIELD_COLUMNS),
        (result.permission_matrix, PERMISSION_CHECK_COLUMNS),
        (result.secrets_scan, SECRETS_SCAN_COLUMNS),
        (result.audit_integrity, AUDIT_INTEGRITY_COLUMNS),
    )
    for frame, columns in expected:
        missing = set(columns).difference(frame.columns)
        if missing:
            raise SecurityControlError(f"security result frame missing columns: {sorted(missing)}")


def build_security_control_quality_summary(result: SecurityControlResult) -> dict[str, object]:
    """Return JSON-serialisable quality summary."""

    restricted = (
        int((result.sensitive_fields["classification"] == "restricted").sum())
        if "classification" in result.sensitive_fields.columns
        else 0
    )
    confidential = (
        int((result.sensitive_fields["classification"] == "confidential").sum())
        if "classification" in result.sensitive_fields.columns
        else 0
    )
    unallowed = (
        int((~result.secrets_scan["allowed"].astype(bool)).sum())
        if "allowed" in result.secrets_scan.columns and not result.secrets_scan.empty
        else 0
    )
    audit_issues = (
        int(result.audit_integrity["issue_count"].fillna(0).sum())
        if "issue_count" in result.audit_integrity.columns
        else 0
    )
    return {
        "security_run_id": result.security_run_id,
        "sensitive_field_count": int(len(result.sensitive_fields)),
        "restricted_field_count": restricted,
        "confidential_field_count": confidential,
        "role_count": int(result.permission_matrix["role"].nunique())
        if "role" in result.permission_matrix.columns
        else 0,
        "protected_action_count": int(
            result.permission_matrix[
                result.permission_matrix.get("metadata", pd.Series(dtype=object)).map(
                    lambda value: isinstance(value, dict) and bool(value.get("protected"))
                )
            ]["action"].nunique()
        )
        if not result.permission_matrix.empty and "metadata" in result.permission_matrix.columns
        else 0,
        "unallowed_secret_finding_count": unallowed,
        "audit_integrity_issue_count": audit_issues,
    }


def run_security_controls_from_inputs(
    inputs: dict[str, object],
    config: SecurityControlConfig | None = None,
) -> SecurityControlResult:
    """Build security control outputs from read inputs."""

    resolved = config or SecurityControlConfig()
    generated_at = pd.Timestamp.utcnow()
    run_id = build_security_run_id(resolved, generated_at)
    try:
        table_columns = inputs.get("table_columns")
        audit_events = inputs.get("audit_events", pd.DataFrame())
        if not isinstance(table_columns, pd.DataFrame):
            raise SecurityControlError("inputs must include table_columns DataFrame")
        if not isinstance(audit_events, pd.DataFrame):
            raise SecurityControlError("audit_events must be a DataFrame")
        sensitive = build_sensitive_field_inventory(table_columns, resolved, run_id)
        permissions = build_permission_matrix(resolved, run_id)
        secrets = run_secrets_scan(resolved, run_id)
        audit = run_audit_integrity_checks(audit_events, resolved, run_id)
        result = SecurityControlResult(
            security_run_id=run_id,
            sensitive_fields=sensitive,
            permission_matrix=permissions,
            secrets_scan=secrets,
            audit_integrity=audit,
            summary={},
            metadata={
                "security_name": resolved.security_name,
                "security_version": resolved.security_version,
                "generated_at": generated_at.isoformat(),
                "input_availability": {
                    key: isinstance(value, pd.DataFrame) and not value.empty
                    for key, value in inputs.items()
                },
                "config_flags": {
                    "masking_enabled": resolved.masking.enabled,
                    "permissions_enabled": resolved.permissions.enabled,
                    "secrets_scan_enabled": resolved.secrets_scan.enabled,
                    "audit_integrity_enabled": resolved.audit_integrity.enabled,
                },
                "fallback_salt_used": True,
            },
        )
        summary = {
            **build_security_control_quality_summary(result),
            "generated_timestamp": generated_at.isoformat(),
        }
        result = SecurityControlResult(
            security_run_id=result.security_run_id,
            sensitive_fields=result.sensitive_fields,
            permission_matrix=result.permission_matrix,
            secrets_scan=result.secrets_scan,
            audit_integrity=result.audit_integrity,
            summary=summary,
            metadata=result.metadata,
        )
        validate_security_control_result(result)
        return result
    except SecurityControlError:
        raise
    except Exception as exc:
        raise SecurityControlError(f"security control workflow failed: {exc}") from exc


def run_and_persist_security_controls(
    engine: Engine,
    security_config: SecurityControlConfig | None = None,
    persistence_config: SecurityControlPersistenceConfig | None = None,
    limit: int | None = None,
    write_artefacts: bool = True,
) -> tuple[SecurityControlResult, SecurityControlPersistenceResult]:
    """Read inputs, build, write artefacts, and optionally persist security outputs."""

    from graph_aml.security.artefacts import generate_security_control_artefacts
    from graph_aml.security.inputs import read_security_inputs
    from graph_aml.security.persistence import (
        SecurityControlPersistenceConfig,
        SecurityControlPersistenceResult,
        persist_security_control_result,
    )

    resolved = security_config or SecurityControlConfig()
    try:
        inputs = read_security_inputs(engine, resolved, limit=limit)
        result = run_security_controls_from_inputs(cast("dict[str, object]", inputs), resolved)
        if write_artefacts and resolved.persistence.write_artefacts:
            generate_security_control_artefacts(result, resolved.persistence.artefact_output_dir)
        persistence = persistence_config or SecurityControlPersistenceConfig(
            security_name=resolved.security_name,
            security_version=resolved.security_version,
            write_audit=resolved.persistence.write_audit,
        )
        if resolved.persistence.write_database:
            persisted = persist_security_control_result(engine, result, resolved, persistence)
        else:
            persisted = SecurityControlPersistenceResult(
                security_run_id=result.security_run_id,
                security_name=resolved.security_name,
                security_version=resolved.security_version,
                metadata=result.metadata,
                summary=result.summary,
            )
        return result, persisted
    except SecurityControlError:
        raise
    except SecurityPersistenceError:
        raise
    except Exception as exc:
        raise SecurityControlError(f"security control run failed: {exc}") from exc
