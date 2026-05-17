"""Read staged PostgreSQL inputs for Neo4j graph loading."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.graph.exceptions import GraphLoadError

GRAPH_CUSTOMER_COLUMNS = (
    "customer_id",
    "customer_type",
    "segment",
    "jurisdiction",
    "occupation",
    "risk_rating",
)
GRAPH_ACCOUNT_COLUMNS = (
    "account_id",
    "customer_id",
    "account_type",
    "opened_at",
    "status",
    "currency",
    "country_code",
)
GRAPH_TRANSACTION_COLUMNS = (
    "transaction_id",
    "transaction_timestamp",
    "sender_account_id",
    "receiver_account_id",
    "counterparty_id",
    "amount",
    "currency",
    "transaction_type",
    "channel",
    "country_code",
    "origin_country",
    "destination_country",
)
GRAPH_COUNTERPARTY_COLUMNS = (
    "counterparty_id",
    "counterparty_type",
    "name",
    "country_code",
    "risk_rating",
)
GRAPH_COUNTRY_COLUMNS = (
    "country_code",
    "country_name",
    "high_risk_flag",
    "region",
)
GRAPH_ALERT_COLUMNS = (
    "alert_id",
    "account_id",
    "customer_id",
    "rule_name",
    "typology",
    "severity",
    "risk_score_rule",
    "reason_code",
    "evidence_ids",
    "detection_window_start",
    "detection_window_end",
    "created_at",
)


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if not isinstance(limit, int) or limit < 0:
        raise GraphLoadError("limit must be a non-negative integer")
    return int(limit)


def _read_query(
    engine: Engine,
    sql: str,
    *,
    limit: int | None,
    table_name: str,
    expected_columns: tuple[str, ...],
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, int] | None = None
    if safe_limit is not None:
        sql = f"{sql}\nLIMIT :limit"
        params = {"limit": safe_limit}
    try:
        frame = pd.read_sql_query(text(sql), engine, params=params)
        if frame.empty:
            return frame.reindex(columns=expected_columns)
        return frame
    except Exception as exc:
        raise GraphLoadError(f"Failed to read {table_name}: {exc}") from exc


def read_graph_customers(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    """Read customer graph rows from staging.customers."""

    return _read_query(
        engine,
        """
        SELECT
            customer_id,
            customer_type,
            customer_segment AS segment,
            jurisdiction,
            occupation,
            customer_risk_rating AS risk_rating
        FROM staging.customers
        ORDER BY customer_id
        """,
        limit=limit,
        table_name="staging.customers",
        expected_columns=GRAPH_CUSTOMER_COLUMNS,
    )


def read_graph_accounts(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    """Read account graph rows from staging.accounts."""

    return _read_query(
        engine,
        """
        SELECT
            account_id,
            customer_id,
            account_type,
            opened_at,
            account_status AS status,
            currency,
            home_country AS country_code
        FROM staging.accounts
        ORDER BY account_id
        """,
        limit=limit,
        table_name="staging.accounts",
        expected_columns=GRAPH_ACCOUNT_COLUMNS,
    )


def read_graph_transactions(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    """Read transaction graph rows from staging.transactions."""

    return _read_query(
        engine,
        """
        SELECT
            transaction_id,
            transaction_timestamp,
            sender_account_id,
            receiver_account_id,
            counterparty_id,
            amount,
            currency,
            transaction_type,
            channel,
            COALESCE(destination_country, origin_country) AS country_code,
            origin_country,
            destination_country
        FROM staging.transactions
        ORDER BY transaction_timestamp, transaction_id
        """,
        limit=limit,
        table_name="staging.transactions",
        expected_columns=GRAPH_TRANSACTION_COLUMNS,
    )


def read_graph_counterparties(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    """Read counterparty graph rows from staging.counterparties."""

    return _read_query(
        engine,
        """
        SELECT
            counterparty_id,
            counterparty_type,
            counterparty_name AS name,
            country_code,
            risk_score AS risk_rating
        FROM staging.counterparties
        ORDER BY counterparty_id
        """,
        limit=limit,
        table_name="staging.counterparties",
        expected_columns=GRAPH_COUNTERPARTY_COLUMNS,
    )


def read_graph_countries(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    """Read country graph rows from staging.countries."""

    return _read_query(
        engine,
        """
        SELECT
            country_code,
            country_name,
            is_high_risk AS high_risk_flag,
            region
        FROM staging.countries
        ORDER BY country_code
        """,
        limit=limit,
        table_name="staging.countries",
        expected_columns=GRAPH_COUNTRY_COLUMNS,
    )


def read_graph_alerts(engine: Engine, limit: int | None = None) -> pd.DataFrame:
    """Read alert graph rows from aml.alerts."""

    return _read_query(
        engine,
        """
        SELECT
            alert_id,
            account_id,
            customer_id,
            rule_name,
            typology,
            severity,
            risk_score_rule,
            reason_code,
            evidence_ids,
            detection_window_start,
            detection_window_end,
            created_at
        FROM aml.alerts
        ORDER BY created_at, alert_id
        """,
        limit=limit,
        table_name="aml.alerts",
        expected_columns=GRAPH_ALERT_COLUMNS,
    )


def read_graph_inputs(
    engine: Engine,
    limit: int | None = None,
    include_alerts: bool = True,
) -> dict[str, pd.DataFrame]:
    """Read all staged graph inputs."""

    try:
        inputs = {
            "customers": read_graph_customers(engine, limit=limit),
            "accounts": read_graph_accounts(engine, limit=limit),
            "transactions": read_graph_transactions(engine, limit=limit),
            "counterparties": read_graph_counterparties(engine, limit=limit),
            "countries": read_graph_countries(engine, limit=limit),
            "alerts": pd.DataFrame(columns=GRAPH_ALERT_COLUMNS),
        }
        if include_alerts:
            inputs["alerts"] = read_graph_alerts(engine, limit=limit)
        return inputs
    except GraphLoadError:
        raise
    except Exception as exc:
        raise GraphLoadError(f"Failed to read graph inputs: {exc}") from exc
