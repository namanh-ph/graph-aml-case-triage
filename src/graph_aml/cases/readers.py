"""Readback utilities for persisted AML cases."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CasePersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CasePersistenceError("limit must be non-negative")
    return int(limit)


def read_cases(
    engine: Engine,
    status: str | None = None,
    severity: str | None = None,
    case_version: str | None = None,
    account_id: str | None = None,
    customer_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if status:
        clauses.append("status = :status")
        params["status"] = status
    if severity:
        clauses.append("severity = :severity")
        params["severity"] = severity
    if case_version:
        clauses.append("case_version = :case_version")
        params["case_version"] = case_version
    if account_id:
        clauses.append("primary_account_id = :account_id")
        params["account_id"] = account_id
    if customer_id:
        clauses.append("primary_customer_id = :customer_id")
        params["customer_id"] = customer_id
    sql = "SELECT * FROM aml.cases"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY priority_score DESC, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CasePersistenceError(f"Failed to read cases: {exc}") from exc


def read_case_alerts(
    engine: Engine,
    case_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM aml.case_alerts"
    if case_id:
        sql += " WHERE case_id = :case_id"
        params["case_id"] = case_id
    sql += " ORDER BY case_id, alert_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CasePersistenceError(f"Failed to read case-alert links: {exc}") from exc


def read_case_entities(
    engine: Engine,
    case_id: str | None = None,
    entity_type: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if case_id:
        clauses.append("case_id = :case_id")
        params["case_id"] = case_id
    if entity_type:
        clauses.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    sql = "SELECT * FROM aml.case_entities"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY case_id, entity_type, entity_id, relationship"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CasePersistenceError(f"Failed to read case entities: {exc}") from exc


def read_case_detail(engine: Engine, case_id: str) -> dict[str, pd.DataFrame]:
    if not case_id.strip():
        raise CasePersistenceError("case_id must be non-empty")
    try:
        case = pd.read_sql_query(
            text("SELECT * FROM aml.cases WHERE case_id = :case_id"),
            engine,
            params={"case_id": case_id},
        )
        return {
            "case": case,
            "alerts": read_case_alerts(engine, case_id=case_id),
            "entities": read_case_entities(engine, case_id=case_id),
        }
    except Exception as exc:
        if isinstance(exc, CasePersistenceError):
            raise
        raise CasePersistenceError(f"Failed to read case detail: {exc}") from exc


def read_case_summary(engine: Engine) -> dict[str, object]:
    sql = """
        SELECT
            COUNT(*) AS case_count,
            COUNT(DISTINCT primary_account_id) AS unique_primary_account_count,
            MAX(priority_score) AS max_priority_score,
            AVG(priority_score) AS mean_priority_score
        FROM aml.cases
    """
    status_sql = "SELECT status, COUNT(*) AS count FROM aml.cases GROUP BY status ORDER BY status"
    severity_sql = (
        "SELECT severity, COUNT(*) AS count FROM aml.cases GROUP BY severity ORDER BY severity"
    )
    strategy_sql = """
        SELECT grouping_strategy, COUNT(*) AS count
        FROM aml.cases
        GROUP BY grouping_strategy
        ORDER BY grouping_strategy
    """
    try:
        base = pd.read_sql_query(text(sql), engine)
        statuses = pd.read_sql_query(text(status_sql), engine)
        severities = pd.read_sql_query(text(severity_sql), engine)
        strategies = pd.read_sql_query(text(strategy_sql), engine)
        row = base.iloc[0].to_dict() if not base.empty else {}
        return {
            "case_count": int(row.get("case_count") or 0),
            "unique_primary_account_count": int(row.get("unique_primary_account_count") or 0),
            "status_counts": {
                str(item["status"]): int(item["count"]) for item in statuses.to_dict("records")
            },
            "severity_counts": {
                str(item["severity"]): int(item["count"]) for item in severities.to_dict("records")
            },
            "grouping_strategy_counts": {
                str(item["grouping_strategy"]): int(item["count"])
                for item in strategies.to_dict("records")
            },
            "max_priority_score": float(row.get("max_priority_score") or 0),
            "mean_priority_score": float(row.get("mean_priority_score") or 0),
        }
    except Exception as exc:
        raise CasePersistenceError(f"Failed to read case summary: {exc}") from exc
