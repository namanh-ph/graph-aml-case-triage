"""Persistence utilities for security control outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import SecurityPersistenceError
from graph_aml.security.validation import SecurityControlResult


@dataclass(frozen=True)
class SecurityControlPersistenceConfig:
    security_name: str = "aml_security_controls"
    security_version: str = "security_controls_v1"
    batch_size: int = 1000
    write_audit: bool = True


@dataclass(frozen=True)
class SecurityControlPersistenceResult:
    security_run_id: str | None = None
    security_run_persisted: bool = False
    sensitive_fields_persisted: int = 0
    permission_rows_persisted: int = 0
    secrets_findings_persisted: int = 0
    audit_integrity_rows_persisted: int = 0
    security_name: str | None = None
    security_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_security_control_persistence_config(config: SecurityControlPersistenceConfig) -> None:
    if not config.security_name.strip() or not config.security_version.strip():
        raise SecurityPersistenceError("security name and version must be non-empty")
    if config.batch_size <= 0:
        raise SecurityPersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise SecurityPersistenceError("write_audit must be boolean")


def build_security_control_run_insert_sql() -> str:
    return """
    INSERT INTO governance.security_control_runs (
        security_run_id, security_name, security_version, sensitive_field_count,
        restricted_field_count, confidential_field_count, unallowed_secret_finding_count,
        audit_integrity_issue_count, summary, metadata
    ) VALUES (
        :security_run_id, :security_name, :security_version, :sensitive_field_count,
        :restricted_field_count, :confidential_field_count, :unallowed_secret_finding_count,
        :audit_integrity_issue_count, CAST(:summary AS jsonb), CAST(:metadata AS jsonb)
    )
    ON CONFLICT (security_run_id) DO NOTHING
    """


def build_sensitive_field_inventory_upsert_sql() -> str:
    return """
    INSERT INTO governance.sensitive_field_inventory (
        security_run_id, schema_name, table_name, column_name, classification,
        matched_pattern, recommended_masking_strategy, metadata
    ) VALUES (
        :security_run_id, :schema_name, :table_name, :column_name, :classification,
        :matched_pattern, :recommended_masking_strategy, CAST(:metadata AS jsonb)
    )
    ON CONFLICT (security_run_id, schema_name, table_name, column_name) DO UPDATE SET
        classification = EXCLUDED.classification,
        matched_pattern = EXCLUDED.matched_pattern,
        recommended_masking_strategy = EXCLUDED.recommended_masking_strategy,
        metadata = EXCLUDED.metadata
    """


def build_permission_matrix_upsert_sql() -> str:
    return """
    INSERT INTO governance.permission_matrix (
        security_run_id, role, action, allowed, reason, metadata
    ) VALUES (
        :security_run_id, :role, :action, :allowed, :reason, CAST(:metadata AS jsonb)
    )
    ON CONFLICT (security_run_id, role, action) DO UPDATE SET
        allowed = EXCLUDED.allowed,
        reason = EXCLUDED.reason,
        metadata = EXCLUDED.metadata
    """


def build_secrets_scan_finding_insert_sql() -> str:
    return """
    INSERT INTO governance.secrets_scan_findings (
        security_run_id, file_path, pattern_name, line_number, match_preview, allowed, metadata
    ) VALUES (
        :security_run_id, :file_path, :pattern_name, :line_number, :match_preview,
        :allowed, CAST(:metadata AS jsonb)
    )
    """


def build_audit_integrity_check_insert_sql() -> str:
    return """
    INSERT INTO governance.audit_integrity_checks (
        security_run_id, check_name, status, issue_count, severity, details, metadata
    ) VALUES (
        :security_run_id, :check_name, :status, :issue_count, :severity,
        CAST(:details AS jsonb), CAST(:metadata AS jsonb)
    )
    """


def _json_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    prepared = frame.astype(object).where(pd.notna(frame), cast(Any, None)).copy()
    for column in columns:
        if column in prepared.columns:
            prepared[column] = [
                json.dumps(value if value is not None else {}, sort_keys=True, default=str)
                for value in prepared[column].tolist()
            ]
    return prepared


def _records(
    frame: pd.DataFrame, json_columns: tuple[str, ...] = ("metadata",)
) -> list[dict[str, object]]:
    if frame.empty:
        return []
    return cast(list[dict[str, object]], _json_columns(frame, json_columns).to_dict("records"))


def _summary_int(summary: dict[str, object], key: str) -> int:
    value = summary.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        return int(value)
    return 0


def persist_security_control_result(
    engine: Engine,
    result: SecurityControlResult,
    config: SecurityControlConfig | None = None,
    persistence_config: SecurityControlPersistenceConfig | None = None,
) -> SecurityControlPersistenceResult:
    """Persist security control outputs."""

    resolved = config or SecurityControlConfig()
    persistence = persistence_config or SecurityControlPersistenceConfig(
        security_name=resolved.security_name,
        security_version=resolved.security_version,
        write_audit=resolved.persistence.write_audit,
    )
    validate_security_control_persistence_config(persistence)
    summary = result.summary
    run_row = {
        "security_run_id": result.security_run_id,
        "security_name": resolved.security_name,
        "security_version": resolved.security_version,
        "sensitive_field_count": len(result.sensitive_fields),
        "restricted_field_count": _summary_int(summary, "restricted_field_count"),
        "confidential_field_count": _summary_int(summary, "confidential_field_count"),
        "unallowed_secret_finding_count": _summary_int(
            summary,
            "unallowed_secret_finding_count",
        ),
        "audit_integrity_issue_count": _summary_int(summary, "audit_integrity_issue_count"),
        "summary": json.dumps(result.summary, sort_keys=True, default=str),
        "metadata": json.dumps(result.metadata, sort_keys=True, default=str),
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(build_security_control_run_insert_sql()), run_row)
            for frame, sql, json_columns in (
                (
                    result.sensitive_fields,
                    build_sensitive_field_inventory_upsert_sql(),
                    ("metadata",),
                ),
                (result.permission_matrix, build_permission_matrix_upsert_sql(), ("metadata",)),
                (result.secrets_scan, build_secrets_scan_finding_insert_sql(), ("metadata",)),
                (
                    result.audit_integrity,
                    build_audit_integrity_check_insert_sql(),
                    ("details", "metadata"),
                ),
            ):
                rows = _records(frame, json_columns)
                if rows:
                    connection.execute(text(sql), rows)
        persisted = SecurityControlPersistenceResult(
            security_run_id=result.security_run_id,
            security_run_persisted=True,
            sensitive_fields_persisted=len(result.sensitive_fields),
            permission_rows_persisted=len(result.permission_matrix),
            secrets_findings_persisted=len(result.secrets_scan),
            audit_integrity_rows_persisted=len(result.audit_integrity),
            security_name=resolved.security_name,
            security_version=resolved.security_version,
            persisted=True,
            metadata=result.metadata,
            summary=result.summary,
        )
        if persistence.write_audit:
            write_security_control_audit_event(engine, persisted, run_id=result.security_run_id)
        return persisted
    except SecurityPersistenceError:
        raise
    except Exception as exc:
        raise SecurityPersistenceError(f"failed to persist security controls: {exc}") from exc


def write_security_control_audit_event(
    engine: Engine,
    result: SecurityControlPersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write a security-controls audit event."""

    sql = """
    INSERT INTO governance.audit_events (
        event_type, component, action, status, run_id, details
    ) VALUES (
        :event_type, :component, :action, :status, :run_id, CAST(:details AS jsonb)
    )
    """
    details = {
        "security_run_id": result.security_run_id,
        "sensitive_fields_persisted": result.sensitive_fields_persisted,
        "permission_rows_persisted": result.permission_rows_persisted,
        "secrets_findings_persisted": result.secrets_findings_persisted,
        "audit_integrity_rows_persisted": result.audit_integrity_rows_persisted,
        "security_name": result.security_name,
        "security_version": result.security_version,
        "summary": result.summary,
        "metadata": result.metadata,
    }
    try:
        with engine.begin() as connection:
            connection.execute(
                text(sql),
                {
                    "event_type": "security_controls",
                    "component": "security",
                    "action": "persist_security_control_result",
                    "status": status,
                    "run_id": run_id or result.security_run_id,
                    "details": json.dumps(details, sort_keys=True, default=str),
                },
            )
    except Exception as exc:
        raise SecurityPersistenceError(f"failed to write security audit event: {exc}") from exc
