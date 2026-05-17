"""PostgreSQL input readers for account risk scoring."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.scoring.config import AccountRiskScoringConfig
from graph_aml.scoring.exceptions import ScoringInputError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise ScoringInputError("limit must be non-negative")
    return int(limit)


def read_scoring_accounts(
    engine: Engine,
    include_inactive_accounts: bool = True,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read account/customer attributes used by component scoring."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if not include_inactive_accounts:
        clauses.append("a.account_status = :active_status")
        params["active_status"] = "active"
    sql = """
        SELECT
            a.account_id,
            a.customer_id,
            a.account_status,
            a.home_country,
            a.currency,
            c.jurisdiction,
            c.customer_risk_rating,
            c.customer_risk_score,
            c.customer_type,
            c.customer_segment,
            fad.high_risk_country_exposure
        FROM staging.accounts a
        LEFT JOIN staging.customers c ON a.customer_id = c.customer_id
        LEFT JOIN (
            SELECT DISTINCT ON (account_id)
                account_id,
                high_risk_country_exposure
            FROM mart.features_account_daily
            ORDER BY account_id, feature_date DESC, feature_version DESC
        ) fad ON a.account_id = fad.account_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY a.account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ScoringInputError(f"Failed to read scoring accounts: {exc}") from exc


def read_scoring_alerts(
    engine: Engine,
    alert_lookback_days: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read persisted AML alerts for rule-risk scoring."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if alert_lookback_days is not None:
        if alert_lookback_days <= 0:
            raise ScoringInputError("alert_lookback_days must be positive")
        clauses.append(
            "created_at >= CURRENT_TIMESTAMP - (:alert_lookback_days * INTERVAL '1 day')"
        )
        params["alert_lookback_days"] = int(alert_lookback_days)
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
        raise ScoringInputError(f"Failed to read scoring alerts: {exc}") from exc


def read_scoring_graph_features(
    engine: Engine,
    feature_date: str | None = None,
    feature_version: str | None = None,
    graph_build_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read persisted graph features for account risk scoring."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if feature_date is not None:
        clauses.append("feature_date = :feature_date")
        params["feature_date"] = feature_date
    if feature_version is not None:
        clauses.append("feature_version = :feature_version")
        params["feature_version"] = feature_version
    if graph_build_id is not None:
        clauses.append("graph_build_id = :graph_build_id")
        params["graph_build_id"] = graph_build_id
    sql = "SELECT * FROM mart.graph_features"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    else:
        sql = """
            WITH latest AS (
                SELECT feature_date, feature_version, graph_build_id
                FROM mart.graph_features
                ORDER BY computed_at DESC, feature_date DESC, feature_version, graph_build_id
                LIMIT 1
            )
            SELECT gf.*
            FROM mart.graph_features gf
            JOIN latest
              ON gf.feature_date = latest.feature_date
             AND gf.feature_version = latest.feature_version
             AND gf.graph_build_id = latest.graph_build_id
        """
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ScoringInputError(f"Failed to read scoring graph features: {exc}") from exc


def read_scoring_anomaly_scores(
    engine: Engine,
    model_version: str | None = None,
    model_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read persisted anomaly scores for account risk scoring."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if model_version is not None:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if model_run_id is not None:
        clauses.append("model_run_id = :model_run_id")
        params["model_run_id"] = model_run_id
    sql = "SELECT * FROM mart.account_anomaly_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    else:
        sql = """
            WITH latest AS (
                SELECT score_date, model_name, model_version, model_run_id
                FROM mart.account_anomaly_scores
                ORDER BY scored_at DESC, score_date DESC, model_version, model_run_id
                LIMIT 1
            )
            SELECT s.*
            FROM mart.account_anomaly_scores s
            JOIN latest
              ON s.score_date = latest.score_date
             AND s.model_name = latest.model_name
             AND s.model_version = latest.model_version
             AND s.model_run_id = latest.model_run_id
        """
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ScoringInputError(f"Failed to read scoring anomaly scores: {exc}") from exc


def read_scoring_feature_inputs(
    engine: Engine,
    config: AccountRiskScoringConfig | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read all persisted inputs required for account risk scoring."""

    resolved = AccountRiskScoringConfig() if config is None else config
    feature_date = resolved.feature_date.isoformat() if resolved.feature_date else None
    return {
        "accounts": read_scoring_accounts(
            engine,
            include_inactive_accounts=resolved.include_inactive_accounts,
            limit=limit,
        ),
        "alerts": read_scoring_alerts(
            engine,
            alert_lookback_days=resolved.alert_lookback_days,
            limit=limit,
        ),
        "graph_features": read_scoring_graph_features(
            engine,
            feature_date=feature_date,
            feature_version=resolved.graph_feature_version,
            graph_build_id=resolved.graph_build_id,
            limit=limit,
        ),
        "anomaly_scores": read_scoring_anomaly_scores(
            engine,
            model_version=resolved.anomaly_model_version,
            model_run_id=resolved.anomaly_model_run_id,
            limit=limit,
        ),
    }
