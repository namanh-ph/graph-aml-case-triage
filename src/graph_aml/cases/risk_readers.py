"""Readback utilities for persisted case-level risk scores."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CaseRiskPersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CaseRiskPersistenceError("limit must be non-negative")
    return int(limit)


def _id_filter(
    case_ids: tuple[str, ...] | list[str] | None,
) -> tuple[str | None, dict[str, object]]:
    if not case_ids:
        return None, {}
    clean = [str(value).strip() for value in case_ids if str(value).strip()]
    if not clean:
        return None, {}
    return "case_id = ANY(:case_ids)", {"case_ids": clean}


def read_case_risk_scores(
    engine: Engine,
    score_date: str | None = None,
    score_name: str | None = None,
    score_version: str | None = None,
    risk_band: str | None = None,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if score_date:
        clauses.append("score_date = :score_date")
        params["score_date"] = score_date
    if score_name:
        clauses.append("score_name = :score_name")
        params["score_name"] = score_name
    if score_version:
        clauses.append("score_version = :score_version")
        params["score_version"] = score_version
    if risk_band:
        clauses.append("risk_band = :risk_band")
        params["risk_band"] = risk_band
    clause, id_params = _id_filter(case_ids)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    sql = "SELECT * FROM aml.case_risk_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_rank, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to read case risk scores: {exc}") from exc


def read_latest_case_risk_scores(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter(case_ids)
    sql = """
        WITH latest AS (
            SELECT score_date, score_name, score_version
            FROM aml.case_risk_scores
            ORDER BY scored_at DESC, score_date DESC, score_version
            LIMIT 1
        )
        SELECT s.*
        FROM aml.case_risk_scores s
        JOIN latest
          ON s.score_date = latest.score_date
         AND s.score_name = latest.score_name
         AND s.score_version = latest.score_version
    """
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY risk_rank, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to read latest case risk scores: {exc}") from exc


def read_case_risk_score_versions(engine: Engine) -> pd.DataFrame:
    sql = """
        SELECT
            score_name,
            score_version,
            score_date,
            COUNT(*) AS row_count,
            MAX(scored_at) AS max_scored_at
        FROM aml.case_risk_scores
        GROUP BY score_name, score_version, score_date
        ORDER BY max_scored_at DESC, score_version
    """
    try:
        return pd.read_sql_query(text(sql), engine)
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to read case risk versions: {exc}") from exc


def read_case_risk_score_summary(engine: Engine) -> dict[str, object]:
    base_sql = """
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT case_id) AS unique_case_count,
            MAX(score_date) AS latest_score_date,
            MAX(scored_at) AS max_scored_at
        FROM aml.case_risk_scores
    """
    latest_sql = """
        SELECT score_name, score_version
        FROM aml.case_risk_scores
        ORDER BY scored_at DESC, score_date DESC, score_version
        LIMIT 1
    """
    band_sql = """
        SELECT risk_band, COUNT(*) AS count
        FROM aml.case_risk_scores
        GROUP BY risk_band
        ORDER BY risk_band
    """
    try:
        base = pd.read_sql_query(text(base_sql), engine)
        latest = pd.read_sql_query(text(latest_sql), engine)
        bands = pd.read_sql_query(text(band_sql), engine)
        row = base.iloc[0].to_dict() if not base.empty else {}
        latest_row = latest.iloc[0].to_dict() if not latest.empty else {}
        return {
            "row_count": int(row.get("row_count") or 0),
            "unique_case_count": int(row.get("unique_case_count") or 0),
            "latest_score_date": str(row.get("latest_score_date"))
            if row.get("latest_score_date") is not None
            else None,
            "latest_score_name": latest_row.get("score_name"),
            "latest_score_version": latest_row.get("score_version"),
            "max_scored_at": str(row.get("max_scored_at"))
            if row.get("max_scored_at") is not None
            else None,
            "risk_band_counts": {
                str(item["risk_band"]): int(item["count"]) for item in bands.to_dict("records")
            },
        }
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to read case risk summary: {exc}") from exc
