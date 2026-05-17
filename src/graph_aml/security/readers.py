"""Readback utilities for persisted security controls."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.security.exceptions import SecurityPersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or limit <= 0:
        raise SecurityPersistenceError("limit must be a positive integer")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine, params=cast(Any, params or {}))
    except Exception as exc:
        raise SecurityPersistenceError(f"security readback failed: {exc}") from exc


def _limit(sql: str, params: dict[str, object], limit: int | None) -> str:
    validated = _validate_limit(limit)
    if validated is not None:
        params["limit"] = validated
        return f"{sql} LIMIT :limit"
    return sql


def read_security_control_runs(
    engine: Engine,
    security_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.security_control_runs WHERE 1=1"
    if security_version:
        sql += " AND security_version = :security_version"
        params["security_version"] = security_version
    sql += " ORDER BY created_at DESC, security_run_id"
    return _read(engine, _limit(sql, params, limit), params)


def read_sensitive_field_inventory(
    engine: Engine,
    security_run_id: str | None = None,
    classification: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.sensitive_field_inventory WHERE 1=1"
    if security_run_id:
        sql += " AND security_run_id = :security_run_id"
        params["security_run_id"] = security_run_id
    if classification:
        sql += " AND classification = :classification"
        params["classification"] = classification
    sql += " ORDER BY schema_name, table_name, column_name"
    return _read(engine, _limit(sql, params, limit), params)


def read_permission_matrix(
    engine: Engine,
    security_run_id: str | None = None,
    role: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.permission_matrix WHERE 1=1"
    if security_run_id:
        sql += " AND security_run_id = :security_run_id"
        params["security_run_id"] = security_run_id
    if role:
        sql += " AND role = :role"
        params["role"] = role
    sql += " ORDER BY role, action"
    return _read(engine, _limit(sql, params, limit), params)


def read_secrets_scan_findings(
    engine: Engine,
    security_run_id: str | None = None,
    allowed: bool | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.secrets_scan_findings WHERE 1=1"
    if security_run_id:
        sql += " AND security_run_id = :security_run_id"
        params["security_run_id"] = security_run_id
    if allowed is not None:
        sql += " AND allowed = :allowed"
        params["allowed"] = bool(allowed)
    sql += " ORDER BY allowed, file_path, line_number"
    return _read(engine, _limit(sql, params, limit), params)


def read_audit_integrity_checks(
    engine: Engine,
    security_run_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.audit_integrity_checks WHERE 1=1"
    if security_run_id:
        sql += " AND security_run_id = :security_run_id"
        params["security_run_id"] = security_run_id
    if status:
        sql += " AND status = :status"
        params["status"] = status
    sql += " ORDER BY created_at DESC, check_name"
    return _read(engine, _limit(sql, params, limit), params)


def read_security_control_summary(engine: Engine) -> dict[str, object]:
    """Read compact security controls summary."""

    runs = read_security_control_runs(engine, limit=1)
    latest_run_id = str(runs.iloc[0]["security_run_id"]) if not runs.empty else None
    latest_version = str(runs.iloc[0]["security_version"]) if not runs.empty else None
    fields = (
        read_sensitive_field_inventory(engine, latest_run_id, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    permissions = (
        read_permission_matrix(engine, latest_run_id, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    secrets = (
        read_secrets_scan_findings(engine, latest_run_id, allowed=False, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    audit = (
        read_audit_integrity_checks(engine, latest_run_id, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    return {
        "security_run_count": int(len(read_security_control_runs(engine, limit=100000))),
        "latest_security_version": latest_version,
        "latest_security_run_id": latest_run_id,
        "sensitive_field_count": int(len(fields)),
        "restricted_field_count": int(
            (fields.get("classification", pd.Series(dtype=str)) == "restricted").sum()
        ),
        "unallowed_secrets_count": int(len(secrets)),
        "audit_integrity_issue_count": int(
            audit.get("issue_count", pd.Series(dtype=int)).fillna(0).sum()
        )
        if not audit.empty
        else 0,
        "permission_row_count": int(len(permissions)),
    }
