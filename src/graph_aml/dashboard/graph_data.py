"""PostgreSQL graph context readers for dashboard graph exploration."""

from __future__ import annotations

import json

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError

GRAPH_VIEW_NODE_COLUMNS = (
    "node_id",
    "node_type",
    "label",
    "risk_score",
    "risk_band",
    "community_id",
    "metadata",
)

GRAPH_VIEW_EDGE_COLUMNS = (
    "source_id",
    "target_id",
    "edge_type",
    "weight",
    "transaction_id",
    "amount",
    "metadata",
)


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise DashboardDataError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(sql), engine, params=params or None)


def _empty_nodes() -> pd.DataFrame:
    return pd.DataFrame(columns=GRAPH_VIEW_NODE_COLUMNS)


def _empty_edges() -> pd.DataFrame:
    return pd.DataFrame(columns=GRAPH_VIEW_EDGE_COLUMNS)


def read_graph_view_seed_accounts(
    engine: Engine,
    case_id: str | None = None,
    account_id: str | None = None,
    community_id: str | None = None,
    risk_band: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read deterministic seed accounts for graph exploration."""

    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    sql = """
        WITH latest_risk AS (
            SELECT DISTINCT ON (account_id) *
            FROM mart.account_risk_scores
            ORDER BY account_id, score_date DESC NULLS LAST, scored_at DESC NULLS LAST
        ),
        latest_graph AS (
            SELECT DISTINCT ON (account_id) *
            FROM mart.graph_features
            ORDER BY account_id, feature_date DESC NULLS LAST, computed_at DESC NULLS LAST
        ),
        selected_accounts AS (
            SELECT :account_id AS account_id WHERE :account_id IS NOT NULL
            UNION
            SELECT primary_account_id AS account_id
            FROM aml.cases
            WHERE :case_id IS NOT NULL AND case_id = :case_id
            UNION
            SELECT entity_id AS account_id
            FROM aml.case_entities
            WHERE :case_id IS NOT NULL
              AND case_id = :case_id
              AND entity_type IN ('account', 'primary_account', 'related_account')
        )
        SELECT
            a.account_id,
            a.customer_id,
            lr.account_risk_score,
            lr.risk_band,
            lg.community_id,
            lg.community_size,
            lg.pagerank_score,
            lg.degree,
            lg.high_risk_alert_count
        FROM staging.accounts a
        LEFT JOIN latest_risk lr ON a.account_id = lr.account_id
        LEFT JOIN latest_graph lg ON a.account_id = lg.account_id
    """
    if account_id:
        params["account_id"] = account_id
    else:
        params["account_id"] = None
    if case_id:
        params["case_id"] = case_id
        clauses.append("a.account_id IN (SELECT account_id FROM selected_accounts)")
    else:
        params["case_id"] = None
    if community_id:
        clauses.append("CAST(lg.community_id AS TEXT) = :community_id")
        params["community_id"] = str(community_id)
    if risk_band:
        clauses.append("lr.risk_band = :risk_band")
        params["risk_band"] = risk_band
    if account_id and not case_id:
        clauses.append("a.account_id = :account_id")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY lr.account_risk_score DESC NULLS LAST, a.account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read graph seed accounts: {exc}") from exc


def read_graph_view_postgres_edges(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str],
    max_hops: int = 2,
    include_transactions: bool = True,
    include_counterparties: bool = True,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read transaction-derived graph edges from PostgreSQL."""

    if max_hops <= 0:
        raise DashboardDataError("max_hops must be positive")
    safe_limit = _validate_limit(limit)
    clean_accounts = [str(value).strip() for value in account_ids if str(value).strip()]
    if not clean_accounts or not include_transactions:
        return _empty_edges()
    params: dict[str, object] = {
        "account_ids": clean_accounts,
        "include_counterparties": include_counterparties,
    }
    sql = """
        SELECT
            sender_account_id AS source_id,
            COALESCE(receiver_account_id, counterparty_id) AS target_id,
            CASE
                WHEN receiver_account_id IS NOT NULL THEN 'transaction_account'
                ELSE 'transaction_counterparty'
            END AS edge_type,
            1.0 AS weight,
            transaction_id,
            amount,
            jsonb_build_object(
                'timestamp', transaction_timestamp,
                'currency', currency,
                'transaction_type', transaction_type,
                'channel', channel
            ) AS metadata
        FROM staging.transactions
        WHERE (
            sender_account_id = ANY(:account_ids)
            OR receiver_account_id = ANY(:account_ids)
        )
        AND (
            :include_counterparties
            OR receiver_account_id IS NOT NULL
        )
        AND COALESCE(receiver_account_id, counterparty_id) IS NOT NULL
        ORDER BY transaction_timestamp DESC, transaction_id
    """
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read graph edges: {exc}") from exc


def _records_to_nodes(frame: pd.DataFrame, node_type: str, id_column: str) -> pd.DataFrame:
    if frame.empty or id_column not in frame.columns:
        return _empty_nodes()
    rows: list[dict[str, object]] = []
    for row in frame.astype(object).to_dict("records"):
        node_id = row.get(id_column)
        if node_id is None or pd.isna(node_id):
            continue
        risk_score = row.get("account_risk_score") or row.get("risk_score_rule")
        rows.append(
            {
                "node_id": str(node_id),
                "node_type": node_type,
                "label": str(node_id),
                "risk_score": risk_score,
                "risk_band": row.get("risk_band") or row.get("severity"),
                "community_id": row.get("community_id"),
                "metadata": json.dumps(row, sort_keys=True, default=str),
            }
        )
    return pd.DataFrame(rows, columns=GRAPH_VIEW_NODE_COLUMNS)


def read_graph_view_context(
    engine: Engine,
    case_id: str | None = None,
    account_id: str | None = None,
    community_id: str | None = None,
    risk_band: str | None = None,
    config: DashboardConfig | None = None,
) -> dict[str, pd.DataFrame]:
    """Build a PostgreSQL-backed graph view context."""

    resolved = config or DashboardConfig()
    try:
        seeds = read_graph_view_seed_accounts(
            engine,
            case_id=case_id,
            account_id=account_id,
            community_id=community_id,
            risk_band=risk_band,
            limit=resolved.graph_view.max_nodes,
        )
        if seeds.empty:
            return {
                "seed_accounts": seeds,
                "nodes": _empty_nodes(),
                "edges": _empty_edges(),
                "transactions": pd.DataFrame(),
                "alerts": pd.DataFrame(),
                "cases": pd.DataFrame(),
            }
        account_ids = tuple(seeds["account_id"].dropna().astype(str).unique())
        edges = read_graph_view_postgres_edges(
            engine,
            account_ids,
            max_hops=resolved.graph_view.max_hops,
            include_transactions=resolved.graph_view.include_transactions,
            include_counterparties=resolved.graph_view.include_counterparties,
            limit=resolved.graph_view.max_edges,
        )
        alerts = pd.DataFrame()
        cases = pd.DataFrame()
        if resolved.graph_view.include_alerts:
            alerts = _read(
                engine,
                """
                    SELECT *
                    FROM aml.alerts
                    WHERE account_id = ANY(:account_ids)
                    ORDER BY risk_score_rule DESC NULLS LAST, created_at DESC NULLS LAST
                """,
                {"account_ids": list(account_ids)},
            )
        if resolved.graph_view.include_cases:
            cases = _read(
                engine,
                """
                    SELECT *
                    FROM aml.cases
                    WHERE primary_account_id = ANY(:account_ids)
                    ORDER BY priority_score DESC NULLS LAST, case_id
                """,
                {"account_ids": list(account_ids)},
            )
        account_nodes = _records_to_nodes(seeds, "account", "account_id")
        counterparty_ids = (
            edges["target_id"].dropna().astype(str).unique().tolist()
            if "target_id" in edges.columns
            else []
        )
        counterparty_nodes = pd.DataFrame(
            [
                {
                    "node_id": value,
                    "node_type": "counterparty" if value not in account_ids else "account",
                    "label": value,
                    "risk_score": None,
                    "risk_band": None,
                    "community_id": None,
                    "metadata": {},
                }
                for value in counterparty_ids
            ],
            columns=GRAPH_VIEW_NODE_COLUMNS,
        )
        alert_nodes = _records_to_nodes(alerts, "alert", "alert_id")
        case_nodes = _records_to_nodes(cases, "case", "case_id")
        node_records: list[dict[str, object]] = []
        for frame in (account_nodes, counterparty_nodes, alert_nodes, case_nodes):
            if not frame.empty:
                node_records.extend(frame.astype(object).to_dict("records"))
        nodes = pd.DataFrame(node_records, columns=GRAPH_VIEW_NODE_COLUMNS)
        return {
            "seed_accounts": seeds,
            "nodes": nodes,
            "edges": edges,
            "transactions": edges.copy(),
            "alerts": alerts,
            "cases": cases,
        }
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to build graph view context: {exc}") from exc
