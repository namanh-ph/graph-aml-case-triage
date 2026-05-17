"""Read persisted graph analytics features from PostgreSQL mart tables."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.graph.exceptions import GraphFeaturePersistenceError
from graph_aml.graph.feature_persistence import (
    GRAPH_FEATURE_TABLE_NAME,
    GRAPH_FEATURE_TABLE_SCHEMA,
)

_TABLE = f"{GRAPH_FEATURE_TABLE_SCHEMA}.{GRAPH_FEATURE_TABLE_NAME}"


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise GraphFeaturePersistenceError("limit must be non-negative")
    return int(limit)


def _filters(
    feature_date: str | None,
    feature_version: str | None,
    graph_build_id: str | None,
    account_ids: tuple[str, ...] | list[str] | None,
) -> tuple[list[str], dict[str, object]]:
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
    if account_ids:
        values = tuple(
            str(account_id).strip() for account_id in account_ids if str(account_id).strip()
        )
        if values:
            clauses.append("account_id = ANY(:account_ids)")
            params["account_ids"] = list(values)
    return clauses, params


def read_graph_features(
    engine: Engine,
    feature_date: str | None = None,
    feature_version: str | None = None,
    graph_build_id: str | None = None,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read graph features with optional filters."""

    safe_limit = _validate_limit(limit)
    clauses, params = _filters(feature_date, feature_version, graph_build_id, account_ids)
    sql = f"SELECT * FROM {_TABLE}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise GraphFeaturePersistenceError(f"Failed to read graph features: {exc}") from exc


def read_latest_graph_features(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read the latest graph feature set by computed timestamp."""

    safe_limit = _validate_limit(limit)
    clauses, params = _filters(None, None, None, account_ids)
    sql = f"""
        WITH latest AS (
            SELECT feature_date, feature_version, graph_build_id
            FROM {_TABLE}
            ORDER BY computed_at DESC, feature_date DESC, feature_version, graph_build_id
            LIMIT 1
        )
        SELECT gf.*
        FROM {_TABLE} gf
        JOIN latest
          ON gf.feature_date = latest.feature_date
         AND gf.feature_version = latest.feature_version
         AND gf.graph_build_id = latest.graph_build_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(f"gf.{clause}" for clause in clauses)
    sql += " ORDER BY gf.account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise GraphFeaturePersistenceError(f"Failed to read latest graph features: {exc}") from exc


def read_graph_feature_versions(engine: Engine) -> pd.DataFrame:
    """Read available graph feature versions and build IDs."""

    try:
        return pd.read_sql_query(
            text(
                f"""
                SELECT
                    feature_date,
                    feature_version,
                    graph_build_id,
                    graph_database,
                    COUNT(*) AS row_count,
                    MAX(computed_at) AS max_computed_at
                FROM {_TABLE}
                GROUP BY feature_date, feature_version, graph_build_id, graph_database
                ORDER BY max_computed_at DESC, feature_date DESC, feature_version, graph_build_id
                """
            ),
            engine,
        )
    except Exception as exc:
        raise GraphFeaturePersistenceError(f"Failed to read graph feature versions: {exc}") from exc


def read_graph_feature_summary(engine: Engine) -> dict[str, object]:
    """Read compact graph feature mart summary."""

    try:
        frame = pd.read_sql_query(
            text(
                f"""
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT account_id) AS unique_account_count,
                    MAX(computed_at) AS max_computed_at
                FROM {_TABLE}
                """
            ),
            engine,
        )
        latest = read_graph_feature_versions(engine)
        if frame.empty:
            return {
                "row_count": 0,
                "unique_account_count": 0,
                "latest_feature_date": None,
                "latest_feature_version": None,
                "latest_graph_build_id": None,
                "max_computed_at": None,
            }
        latest_row = latest.iloc[0] if not latest.empty else {}
        return {
            "row_count": int(frame.loc[0, "row_count"] or 0),
            "unique_account_count": int(frame.loc[0, "unique_account_count"] or 0),
            "latest_feature_date": str(latest_row.get("feature_date")) if len(latest_row) else None,
            "latest_feature_version": str(latest_row.get("feature_version"))
            if len(latest_row)
            else None,
            "latest_graph_build_id": str(latest_row.get("graph_build_id"))
            if len(latest_row)
            else None,
            "max_computed_at": str(frame.loc[0, "max_computed_at"])
            if not pd.isna(frame.loc[0, "max_computed_at"])
            else None,
        }
    except GraphFeaturePersistenceError:
        raise
    except Exception as exc:
        raise GraphFeaturePersistenceError(f"Failed to read graph feature summary: {exc}") from exc
