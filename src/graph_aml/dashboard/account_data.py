"""Account profile PostgreSQL readers for the dashboard."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise DashboardDataError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(sql), engine, params=params or None)


def _require_account_id(account_id: str) -> str:
    clean = str(account_id).strip()
    if not clean:
        raise DashboardDataError("account_id must be non-empty")
    return clean


def read_account_profile_header(engine: Engine, account_id: str) -> pd.DataFrame:
    clean = _require_account_id(account_id)
    sql = """
        WITH latest_risk AS (
            SELECT DISTINCT ON (account_id) *
            FROM mart.account_risk_scores
            ORDER BY account_id, score_date DESC NULLS LAST, scored_at DESC NULLS LAST
        ),
        latest_anomaly AS (
            SELECT DISTINCT ON (account_id) *
            FROM mart.account_anomaly_scores
            ORDER BY account_id, score_date DESC NULLS LAST, scored_at DESC NULLS LAST
        ),
        latest_graph AS (
            SELECT DISTINCT ON (account_id) *
            FROM mart.graph_features
            ORDER BY account_id, feature_date DESC NULLS LAST, computed_at DESC NULLS LAST
        )
        SELECT
            a.*,
            c.customer_name,
            c.customer_segment,
            c.customer_risk_rating,
            c.jurisdiction AS customer_country_code,
            lr.account_risk_score,
            lr.risk_band AS account_risk_band,
            la.anomaly_score,
            la.risk_band AS anomaly_risk_band,
            lg.community_id,
            lg.community_size
        FROM staging.accounts a
        LEFT JOIN staging.customers c ON a.customer_id = c.customer_id
        LEFT JOIN latest_risk lr ON a.account_id = lr.account_id
        LEFT JOIN latest_anomaly la ON a.account_id = la.account_id
        LEFT JOIN latest_graph lg ON a.account_id = lg.account_id
        WHERE a.account_id = :account_id
    """
    try:
        return _read(engine, sql, {"account_id": clean})
    except Exception as exc:
        raise DashboardDataError(f"Failed to read account profile header: {exc}") from exc


def read_account_profile_transactions(
    engine: Engine,
    account_id: str,
    lookback_days: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    clean = _require_account_id(account_id)
    safe_limit = _validate_limit(limit)
    if lookback_days is not None and lookback_days <= 0:
        raise DashboardDataError("lookback_days must be positive")
    params: dict[str, object] = {"account_id": clean}
    sql = """
        SELECT *
        FROM staging.transactions
        WHERE sender_account_id = :account_id OR receiver_account_id = :account_id
    """
    if lookback_days is not None:
        sql += (
            " AND transaction_timestamp >= "
            "CURRENT_TIMESTAMP - (:lookback_days || ' days')::interval"
        )
        params["lookback_days"] = int(lookback_days)
    sql += " ORDER BY transaction_timestamp DESC, transaction_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read account transactions: {exc}") from exc


def read_account_profile_alerts(
    engine: Engine,
    account_id: str,
    limit: int | None = None,
) -> pd.DataFrame:
    clean = _require_account_id(account_id)
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {"account_id": clean}
    sql = """
        SELECT *
        FROM aml.alerts
        WHERE account_id = :account_id
        ORDER BY risk_score_rule DESC NULLS LAST, created_at DESC NULLS LAST, alert_id
    """
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read account alerts: {exc}") from exc


def read_account_profile_cases(
    engine: Engine,
    account_id: str,
    limit: int | None = None,
) -> pd.DataFrame:
    clean = _require_account_id(account_id)
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {"account_id": clean}
    sql = """
        WITH latest_scores AS (
            SELECT DISTINCT ON (case_id) *
            FROM aml.case_risk_scores
            ORDER BY case_id, scored_at DESC NULLS LAST, case_risk_score DESC NULLS LAST
        ),
        linked_cases AS (
            SELECT * FROM aml.cases WHERE primary_account_id = :account_id
            UNION
            SELECT c.*
            FROM aml.cases c
            JOIN aml.case_entities ce ON c.case_id = ce.case_id
            WHERE ce.entity_id = :account_id
        )
        SELECT lc.*, rs.case_risk_score, rs.risk_band, rs.risk_rank
        FROM linked_cases lc
        LEFT JOIN latest_scores rs ON lc.case_id = rs.case_id
        ORDER BY rs.case_risk_score DESC NULLS LAST, lc.priority_score DESC NULLS LAST, lc.case_id
    """
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read linked account cases: {exc}") from exc


def read_account_profile_features(engine: Engine, account_id: str) -> dict[str, pd.DataFrame]:
    clean = _require_account_id(account_id)
    params: dict[str, object] = {"account_id": clean}
    try:
        return {
            "behavioural_features": _read(
                engine,
                """
                    SELECT *
                    FROM mart.features_account_daily
                    WHERE account_id = :account_id
                    ORDER BY feature_date DESC, feature_version
                """,
                params,
            ),
            "graph_features": _read(
                engine,
                """
                    SELECT *
                    FROM mart.graph_features
                    WHERE account_id = :account_id
                    ORDER BY feature_date DESC NULLS LAST, computed_at DESC NULLS LAST
                """,
                params,
            ),
            "anomaly_scores": _read(
                engine,
                """
                    SELECT *
                    FROM mart.account_anomaly_scores
                    WHERE account_id = :account_id
                    ORDER BY score_date DESC NULLS LAST, scored_at DESC NULLS LAST
                """,
                params,
            ),
            "account_risk_scores": _read(
                engine,
                """
                    SELECT *
                    FROM mart.account_risk_scores
                    WHERE account_id = :account_id
                    ORDER BY score_date DESC NULLS LAST, scored_at DESC NULLS LAST
                """,
                params,
            ),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to read account profile features: {exc}") from exc


def read_account_profile_counterparties(
    engine: Engine,
    account_id: str,
    limit: int | None = None,
) -> pd.DataFrame:
    clean = _require_account_id(account_id)
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {"account_id": clean}
    sql = """
        SELECT
            COALESCE(receiver_account_id, counterparty_id, sender_account_id) AS counterparty_key,
            COUNT(*) AS transaction_count,
            SUM(amount) AS total_amount,
            MAX(transaction_timestamp) AS latest_transaction_timestamp
        FROM staging.transactions
        WHERE sender_account_id = :account_id OR receiver_account_id = :account_id
        GROUP BY COALESCE(receiver_account_id, counterparty_id, sender_account_id)
        ORDER BY total_amount DESC NULLS LAST, counterparty_key
    """
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read account counterparties: {exc}") from exc


def read_account_profile(
    engine: Engine,
    account_id: str,
    config: DashboardConfig | None = None,
) -> dict[str, pd.DataFrame]:
    resolved = config or DashboardConfig()
    return {
        "header": read_account_profile_header(engine, account_id),
        "transactions": read_account_profile_transactions(
            engine,
            account_id,
            lookback_days=resolved.account_profile.transaction_lookback_days,
            limit=resolved.account_profile.max_transactions,
        ),
        "alerts": read_account_profile_alerts(
            engine, account_id, limit=resolved.account_profile.max_alerts
        ),
        "cases": read_account_profile_cases(
            engine, account_id, limit=resolved.account_profile.max_cases
        ),
        "counterparties": read_account_profile_counterparties(
            engine, account_id, limit=resolved.account_profile.max_counterparties
        ),
        **read_account_profile_features(engine, account_id),
    }
