"""Read persisted anomaly scores from PostgreSQL mart tables."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.models.exceptions import ModelPersistenceError
from graph_aml.models.persistence import (
    ANOMALY_SCORE_TABLE_NAME,
    ANOMALY_SCORE_TABLE_SCHEMA,
)

_TABLE = f"{ANOMALY_SCORE_TABLE_SCHEMA}.{ANOMALY_SCORE_TABLE_NAME}"


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise ModelPersistenceError("limit must be non-negative")
    return int(limit)


def _filters(
    score_date: str | None,
    model_name: str | None,
    model_version: str | None,
    model_run_id: str | None,
    risk_band: str | None,
    account_ids: tuple[str, ...] | list[str] | None,
) -> tuple[list[str], dict[str, object]]:
    clauses: list[str] = []
    params: dict[str, object] = {}
    if score_date is not None:
        clauses.append("score_date = :score_date")
        params["score_date"] = score_date
    if model_name is not None:
        clauses.append("model_name = :model_name")
        params["model_name"] = model_name
    if model_version is not None:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if model_run_id is not None:
        clauses.append("model_run_id = :model_run_id")
        params["model_run_id"] = model_run_id
    if risk_band is not None:
        if risk_band not in {"low", "medium", "high"}:
            raise ModelPersistenceError("risk_band must be low, medium, or high")
        clauses.append("risk_band = :risk_band")
        params["risk_band"] = risk_band
    if account_ids:
        values = tuple(
            str(account_id).strip() for account_id in account_ids if str(account_id).strip()
        )
        if values:
            clauses.append("account_id = ANY(:account_ids)")
            params["account_ids"] = list(values)
    return clauses, params


def read_anomaly_scores(
    engine: Engine,
    score_date: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    model_run_id: str | None = None,
    risk_band: str | None = None,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read anomaly scores with optional filters."""

    safe_limit = _validate_limit(limit)
    clauses, params = _filters(
        score_date,
        model_name,
        model_version,
        model_run_id,
        risk_band,
        account_ids,
    )
    sql = f"SELECT * FROM {_TABLE}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY anomaly_rank, account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to read anomaly scores: {exc}") from exc


def read_latest_anomaly_scores(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read the latest anomaly score set by scored timestamp."""

    safe_limit = _validate_limit(limit)
    clauses, params = _filters(None, None, None, None, None, account_ids)
    sql = f"""
        WITH latest AS (
            SELECT score_date, model_name, model_version, model_run_id
            FROM {_TABLE}
            ORDER BY scored_at DESC, score_date DESC, model_version, model_run_id
            LIMIT 1
        )
        SELECT scores.*
        FROM {_TABLE} scores
        JOIN latest
          ON scores.score_date = latest.score_date
         AND scores.model_name = latest.model_name
         AND scores.model_version = latest.model_version
         AND scores.model_run_id = latest.model_run_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(f"scores.{clause}" for clause in clauses)
    sql += " ORDER BY scores.anomaly_rank, scores.account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to read latest anomaly scores: {exc}") from exc


def read_anomaly_score_versions(engine: Engine) -> pd.DataFrame:
    """Read available anomaly score versions and model run IDs."""

    try:
        return pd.read_sql_query(
            text(
                f"""
                SELECT
                    score_date,
                    model_name,
                    model_version,
                    model_run_id,
                    COUNT(*) AS row_count,
                    MAX(scored_at) AS max_scored_at
                FROM {_TABLE}
                GROUP BY score_date, model_name, model_version, model_run_id
                ORDER BY max_scored_at DESC, score_date DESC, model_version, model_run_id
                """
            ),
            engine,
        )
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to read anomaly score versions: {exc}") from exc


def read_anomaly_score_summary(engine: Engine) -> dict[str, object]:
    """Read compact anomaly score mart summary."""

    try:
        frame = pd.read_sql_query(
            text(
                f"""
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT account_id) AS unique_account_count,
                    MAX(scored_at) AS max_scored_at
                FROM {_TABLE}
                """
            ),
            engine,
        )
        bands = pd.read_sql_query(
            text(
                f"""
                SELECT risk_band, COUNT(*) AS row_count
                FROM {_TABLE}
                GROUP BY risk_band
                ORDER BY risk_band
                """
            ),
            engine,
        )
        latest = read_anomaly_score_versions(engine)
        if frame.empty:
            return {
                "row_count": 0,
                "unique_account_count": 0,
                "latest_score_date": None,
                "latest_model_name": None,
                "latest_model_version": None,
                "latest_model_run_id": None,
                "max_scored_at": None,
                "risk_band_counts": {},
            }
        latest_row = latest.iloc[0] if not latest.empty else {}
        risk_band_counts = {
            str(row["risk_band"]): int(row["row_count"]) for _, row in bands.iterrows()
        }
        return {
            "row_count": int(frame.loc[0, "row_count"] or 0),
            "unique_account_count": int(frame.loc[0, "unique_account_count"] or 0),
            "latest_score_date": str(latest_row.get("score_date")) if len(latest_row) else None,
            "latest_model_name": str(latest_row.get("model_name")) if len(latest_row) else None,
            "latest_model_version": str(latest_row.get("model_version"))
            if len(latest_row)
            else None,
            "latest_model_run_id": str(latest_row.get("model_run_id")) if len(latest_row) else None,
            "max_scored_at": str(frame.loc[0, "max_scored_at"])
            if not pd.isna(frame.loc[0, "max_scored_at"])
            else None,
            "risk_band_counts": risk_band_counts,
        }
    except ModelPersistenceError:
        raise
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to read anomaly score summary: {exc}") from exc
