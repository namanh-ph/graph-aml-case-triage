"""PostgreSQL readers for case generation inputs."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.config import CaseGenerationConfig
from graph_aml.cases.exceptions import CaseInputError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CaseInputError("limit must be non-negative")
    return int(limit)


def read_case_alerts(
    engine: Engine,
    lookback_days: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if lookback_days is not None:
        if lookback_days <= 0:
            raise CaseInputError("lookback_days must be positive")
        clauses.append("created_at >= CURRENT_TIMESTAMP - (:lookback_days * INTERVAL '1 day')")
        params["lookback_days"] = int(lookback_days)
    sql = "SELECT * FROM aml.alerts"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY account_id, alert_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseInputError(f"Failed to read case alerts: {exc}") from exc


def read_case_accounts(
    engine: Engine,
    include_inactive_accounts: bool = True,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = """
        SELECT
            a.account_id,
            a.customer_id,
            a.account_status,
            c.customer_risk_rating,
            c.jurisdiction
        FROM staging.accounts a
        LEFT JOIN staging.customers c ON a.customer_id = c.customer_id
    """
    if not include_inactive_accounts:
        sql += " WHERE a.account_status = :active_status"
        params["active_status"] = "active"
    sql += " ORDER BY a.account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseInputError(f"Failed to read case accounts: {exc}") from exc


def read_case_account_risk_scores(
    engine: Engine,
    score_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    if score_version:
        sql = "SELECT * FROM mart.account_risk_scores WHERE score_version = :score_version"
        params["score_version"] = score_version
    else:
        sql = """
            WITH latest AS (
                SELECT score_date, score_name, score_version
                FROM mart.account_risk_scores
                ORDER BY scored_at DESC, score_date DESC, score_version
                LIMIT 1
            )
            SELECT s.*
            FROM mart.account_risk_scores s
            JOIN latest
              ON s.score_date = latest.score_date
             AND s.score_name = latest.score_name
             AND s.score_version = latest.score_version
        """
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseInputError(f"Failed to read account risk scores: {exc}") from exc


def read_case_graph_features(
    engine: Engine,
    feature_version: str | None = None,
    graph_build_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if feature_version:
        clauses.append("feature_version = :feature_version")
        params["feature_version"] = feature_version
    if graph_build_id:
        clauses.append("graph_build_id = :graph_build_id")
        params["graph_build_id"] = graph_build_id
    sql = "SELECT * FROM mart.graph_features"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseInputError(f"Failed to read graph features: {exc}") from exc


def read_case_transactions(
    engine: Engine,
    transaction_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if transaction_ids:
        values = [str(value).strip() for value in transaction_ids if str(value).strip()]
        if values:
            clauses.append("transaction_id = ANY(:transaction_ids)")
            params["transaction_ids"] = values
    sql = "SELECT * FROM staging.transactions"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY transaction_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseInputError(f"Failed to read case transactions: {exc}") from exc


def read_case_inputs(
    engine: Engine,
    config: CaseGenerationConfig | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    resolved = CaseGenerationConfig() if config is None else config
    return {
        "alerts": read_case_alerts(engine, resolved.thresholds.lookback_days, limit=limit),
        "accounts": read_case_accounts(engine, limit=limit),
        "account_risk_scores": read_case_account_risk_scores(engine, limit=limit),
        "graph_features": read_case_graph_features(engine, limit=limit),
        "transactions": read_case_transactions(engine, limit=limit),
    }
