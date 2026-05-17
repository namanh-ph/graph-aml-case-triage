"""Input readers for governance inventory construction."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.governance.config import GovernanceInventoryConfig
from graph_aml.governance.exceptions import GovernanceInventoryInputError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or int(limit) < 0:
        raise GovernanceInventoryInputError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    return pd.read_sql_query(
        text(sql),
        engine,
        params=cast("dict[str, Any] | None", params or None),
    )


def _limited_sql(base_sql: str, order_by: str, limit: int | None, params: dict[str, object]) -> str:
    sql = f"{base_sql} ORDER BY {order_by}"
    safe_limit = _validate_limit(limit)
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return sql


def read_governance_table_counts(engine: Engine) -> pd.DataFrame:
    """Read approximate row counts for relevant database schemas."""

    sql = """
    SELECT
        schemaname AS schema_name,
        relname AS table_name,
        COALESCE(n_live_tup, 0) AS row_count
    FROM pg_stat_user_tables
    WHERE schemaname IN ('raw', 'staging', 'mart', 'aml', 'governance')
    ORDER BY schemaname, relname
    """
    try:
        return _read(engine, sql)
    except Exception as exc:
        raise GovernanceInventoryInputError(
            f"failed to read governance table counts: {exc}"
        ) from exc


def read_governance_audit_events(
    engine: Engine,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = _limited_sql(
        """
        SELECT *
        FROM governance.audit_events
        """,
        "event_timestamp DESC NULLS LAST, audit_event_id DESC",
        limit,
        params,
    )
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryInputError(
            f"failed to read governance audit events: {exc}"
        ) from exc


def _read_table(
    engine: Engine,
    table_name: str,
    order_by: str,
    limit: int | None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = _limited_sql(f"SELECT * FROM {table_name}", order_by, limit, params)
    return _read(engine, sql, params)


def read_governance_model_runs(
    engine: Engine,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read model inventory source run tables."""

    try:
        return {
            "model_runs": _read_table(
                engine,
                "governance.model_runs",
                "created_at DESC NULLS LAST, model_run_id",
                limit,
            ),
            "supervised_model_runs": _read_table(
                engine,
                "governance.supervised_model_runs",
                "trained_at DESC NULLS LAST, run_id",
                limit,
            ),
        }
    except Exception as exc:
        raise GovernanceInventoryInputError(f"failed to read governance model runs: {exc}") from exc


def read_governance_validation_runs(
    engine: Engine,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read validation, monitoring, and explainability run tables."""

    try:
        return {
            "model_comparison_runs": _read_table(
                engine,
                "governance.model_comparison_runs",
                "created_at DESC NULLS LAST, comparison_run_id",
                limit,
            ),
            "monitoring_runs": _read_table(
                engine,
                "governance.monitoring_runs",
                "created_at DESC NULLS LAST, monitoring_run_id",
                limit,
            ),
            "explainability_runs": _read_table(
                engine,
                "governance.explainability_runs",
                "created_at DESC NULLS LAST, explanation_run_id",
                limit,
            ),
        }
    except Exception as exc:
        raise GovernanceInventoryInputError(
            f"failed to read governance validation runs: {exc}"
        ) from exc


def read_governance_inventory_inputs(
    engine: Engine,
    config: GovernanceInventoryConfig | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    """Read all persisted inputs needed for the governance inventory."""

    resolved = config or GovernanceInventoryConfig()
    inputs: dict[str, object] = {}
    if resolved.include.database_tables:
        inputs["table_counts"] = read_governance_table_counts(engine)
    else:
        inputs["table_counts"] = pd.DataFrame()
    if resolved.include.audit_events:
        inputs["audit_events"] = read_governance_audit_events(engine, limit=limit)
    else:
        inputs["audit_events"] = pd.DataFrame()
    model_runs = read_governance_model_runs(engine, limit=limit)
    if not resolved.include.model_runs:
        model_runs["model_runs"] = pd.DataFrame()
    if not resolved.include.supervised_model_runs:
        model_runs["supervised_model_runs"] = pd.DataFrame()
    inputs["model_runs"] = model_runs
    validation_runs = read_governance_validation_runs(engine, limit=limit)
    if not resolved.include.model_comparison_runs:
        validation_runs["model_comparison_runs"] = pd.DataFrame()
    if not resolved.include.monitoring_runs:
        validation_runs["monitoring_runs"] = pd.DataFrame()
    if not resolved.include.explainability_runs:
        validation_runs["explainability_runs"] = pd.DataFrame()
    inputs["validation_runs"] = validation_runs
    return inputs
