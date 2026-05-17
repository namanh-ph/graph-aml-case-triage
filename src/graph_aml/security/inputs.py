"""PostgreSQL readers for security control inputs."""

from __future__ import annotations

import re
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import SecurityPersistenceError

PROJECT_SCHEMAS = ("raw", "staging", "mart", "aml", "governance")
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or limit <= 0:
        raise SecurityPersistenceError("limit must be a positive integer")
    return int(limit)


def _read_sql(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine, params=cast(Any, params or {}))
    except Exception as exc:
        raise SecurityPersistenceError(f"security input read failed: {exc}") from exc


def read_security_table_columns(engine: Engine) -> pd.DataFrame:
    """Read project table columns from information_schema."""

    sql = """
    SELECT table_schema AS schema_name, table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = ANY(:schemas)
    ORDER BY table_schema, table_name, ordinal_position
    """
    return _read_sql(engine, sql, {"schemas": list(PROJECT_SCHEMAS)})


def read_security_audit_events(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    validated = _validate_limit(limit)
    sql = """
    SELECT *
    FROM governance.audit_events
    ORDER BY created_at DESC, audit_event_id DESC
    """
    params: dict[str, object] = {}
    if validated is not None:
        sql += " LIMIT :limit"
        params["limit"] = validated
    return _read_sql(engine, sql, params)


def read_security_sample_table(
    engine: Engine,
    schema_name: str,
    table_name: str,
    limit: int | None = 100,
) -> pd.DataFrame:
    """Read a bounded sample from a validated project table."""

    if schema_name not in PROJECT_SCHEMAS:
        raise SecurityPersistenceError("schema is not allowed for security preview")
    if not SAFE_IDENTIFIER.match(table_name):
        raise SecurityPersistenceError("table name is unsafe")
    validated = _validate_limit(limit)
    sql = f'SELECT * FROM "{schema_name}"."{table_name}" ORDER BY 1'
    params: dict[str, object] = {}
    if validated is not None:
        sql += " LIMIT :limit"
        params["limit"] = validated
    return _read_sql(engine, sql, params)


def read_security_inputs(
    engine: Engine,
    config: SecurityControlConfig | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    """Read all inputs needed for security control execution."""

    _ = config or SecurityControlConfig()
    return {
        "table_columns": read_security_table_columns(engine),
        "audit_events": read_security_audit_events(engine, limit=limit),
    }
