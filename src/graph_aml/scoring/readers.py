"""Read persisted composite account risk scores."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.scoring.exceptions import ScoringPersistenceError
from graph_aml.scoring.persistence import (
    ACCOUNT_RISK_SCORE_TABLE_NAME,
    ACCOUNT_RISK_SCORE_TABLE_SCHEMA,
)

_TABLE = f"{ACCOUNT_RISK_SCORE_TABLE_SCHEMA}.{ACCOUNT_RISK_SCORE_TABLE_NAME}"


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise ScoringPersistenceError("limit must be non-negative")
    return int(limit)


def _filters(
    score_date: str | None,
    score_name: str | None,
    score_version: str | None,
    risk_band: str | None,
    account_ids: tuple[str, ...] | list[str] | None,
) -> tuple[list[str], dict[str, object]]:
    clauses: list[str] = []
    params: dict[str, object] = {}
    if score_date is not None:
        clauses.append("score_date = :score_date")
        params["score_date"] = score_date
    if score_name is not None:
        clauses.append("score_name = :score_name")
        params["score_name"] = score_name
    if score_version is not None:
        clauses.append("score_version = :score_version")
        params["score_version"] = score_version
    if risk_band is not None:
        if risk_band not in {"low", "medium", "high", "critical"}:
            raise ScoringPersistenceError("risk_band must be low, medium, high, or critical")
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


def read_account_risk_scores(
    engine: Engine,
    score_date: str | None = None,
    score_name: str | None = None,
    score_version: str | None = None,
    risk_band: str | None = None,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read account risk scores with optional filters."""

    safe_limit = _validate_limit(limit)
    clauses, params = _filters(score_date, score_name, score_version, risk_band, account_ids)
    sql = f"SELECT * FROM {_TABLE}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_rank, account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to read account risk scores: {exc}") from exc


def read_latest_account_risk_scores(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read latest account risk score set by scored timestamp."""

    safe_limit = _validate_limit(limit)
    clauses, params = _filters(None, None, None, None, account_ids)
    sql = f"""
        WITH latest AS (
            SELECT score_date, score_name, score_version
            FROM {_TABLE}
            ORDER BY scored_at DESC, score_date DESC, score_version
            LIMIT 1
        )
        SELECT scores.*
        FROM {_TABLE} scores
        JOIN latest
          ON scores.score_date = latest.score_date
         AND scores.score_name = latest.score_name
         AND scores.score_version = latest.score_version
    """
    if clauses:
        sql += " WHERE " + " AND ".join(f"scores.{clause}" for clause in clauses)
    sql += " ORDER BY scores.risk_rank, scores.account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to read latest account risk scores: {exc}") from exc


def read_account_risk_score_versions(engine: Engine) -> pd.DataFrame:
    """Read available account risk score versions."""

    try:
        return pd.read_sql_query(
            text(
                f"""
                SELECT
                    score_date,
                    score_name,
                    score_version,
                    COUNT(*) AS row_count,
                    MAX(scored_at) AS max_scored_at
                FROM {_TABLE}
                GROUP BY score_date, score_name, score_version
                ORDER BY max_scored_at DESC, score_date DESC, score_version
                """
            ),
            engine,
        )
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to read account risk score versions: {exc}") from exc


def read_account_risk_score_summary(engine: Engine) -> dict[str, object]:
    """Read compact account risk score mart summary."""

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
        latest = read_account_risk_score_versions(engine)
        if frame.empty:
            return {
                "row_count": 0,
                "unique_account_count": 0,
                "latest_score_date": None,
                "latest_score_name": None,
                "latest_score_version": None,
                "max_scored_at": None,
                "risk_band_counts": {},
            }
        latest_row = latest.iloc[0] if not latest.empty else {}
        return {
            "row_count": int(frame.loc[0, "row_count"] or 0),
            "unique_account_count": int(frame.loc[0, "unique_account_count"] or 0),
            "latest_score_date": str(latest_row.get("score_date")) if len(latest_row) else None,
            "latest_score_name": str(latest_row.get("score_name")) if len(latest_row) else None,
            "latest_score_version": str(latest_row.get("score_version"))
            if len(latest_row)
            else None,
            "max_scored_at": str(frame.loc[0, "max_scored_at"])
            if not pd.isna(frame.loc[0, "max_scored_at"])
            else None,
            "risk_band_counts": {
                str(row["risk_band"]): int(row["row_count"]) for _, row in bands.iterrows()
            },
        }
    except ScoringPersistenceError:
        raise
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to read account risk score summary: {exc}") from exc
