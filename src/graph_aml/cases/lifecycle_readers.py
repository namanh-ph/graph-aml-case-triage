"""Readback utilities for AML case lifecycle records."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CaseLifecyclePersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CaseLifecyclePersistenceError("limit must be non-negative")
    return int(limit)


def read_case_current_status(engine: Engine, case_id: str) -> str | None:
    if not case_id.strip():
        raise CaseLifecyclePersistenceError("case_id must be non-empty")
    try:
        frame = pd.read_sql_query(
            text("SELECT status FROM aml.cases WHERE case_id = :case_id"),
            engine,
            params={"case_id": case_id},
        )
        if frame.empty:
            return None
        value = frame.iloc[0].get("status")
        return None if pd.isna(value) else str(value)
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to read case status: {exc}") from exc


def read_case_lifecycle_events(
    engine: Engine,
    case_id: str | None = None,
    analyst_id: str | None = None,
    action_type: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if case_id:
        clauses.append("case_id = :case_id")
        params["case_id"] = case_id
    if analyst_id:
        clauses.append("analyst_id = :analyst_id")
        params["analyst_id"] = analyst_id
    if action_type:
        clauses.append("action_type = :action_type")
        params["action_type"] = action_type
    sql = "SELECT * FROM aml.case_lifecycle_events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY action_timestamp DESC, action_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to read lifecycle events: {exc}") from exc


def read_case_assignments(
    engine: Engine,
    assigned_to: str | None = None,
    queue: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if assigned_to:
        clauses.append("assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to
    if queue:
        clauses.append("queue = :queue")
        params["queue"] = queue
    sql = "SELECT * FROM aml.case_assignments"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY assigned_at DESC, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to read case assignments: {exc}") from exc


def read_case_lifecycle_summary(engine: Engine) -> dict[str, object]:
    event_sql = """
        SELECT
            COUNT(*) AS lifecycle_event_count,
            COUNT(DISTINCT case_id) AS lifecycle_case_count,
            MAX(action_timestamp) AS latest_action_timestamp
        FROM aml.case_lifecycle_events
    """
    assignment_sql = "SELECT COUNT(*) AS assigned_case_count FROM aml.case_assignments"
    action_sql = """
        SELECT action_type, COUNT(*) AS count
        FROM aml.case_lifecycle_events
        GROUP BY action_type
        ORDER BY action_type
    """
    analyst_sql = """
        SELECT analyst_id, COUNT(*) AS count
        FROM aml.case_lifecycle_events
        GROUP BY analyst_id
        ORDER BY analyst_id
    """
    status_sql = "SELECT status, COUNT(*) AS count FROM aml.cases GROUP BY status ORDER BY status"
    try:
        base = pd.read_sql_query(text(event_sql), engine)
        assignments = pd.read_sql_query(text(assignment_sql), engine)
        actions = pd.read_sql_query(text(action_sql), engine)
        analysts = pd.read_sql_query(text(analyst_sql), engine)
        statuses = pd.read_sql_query(text(status_sql), engine)
        row = base.iloc[0].to_dict() if not base.empty else {}
        assignment_row = assignments.iloc[0].to_dict() if not assignments.empty else {}
        latest = row.get("latest_action_timestamp")
        return {
            "lifecycle_event_count": int(row.get("lifecycle_event_count") or 0),
            "lifecycle_case_count": int(row.get("lifecycle_case_count") or 0),
            "assigned_case_count": int(assignment_row.get("assigned_case_count") or 0),
            "events_by_action_type": {
                str(item["action_type"]): int(item["count"]) for item in actions.to_dict("records")
            },
            "events_by_analyst": {
                str(item["analyst_id"]): int(item["count"]) for item in analysts.to_dict("records")
            },
            "current_case_status_counts": {
                str(item["status"]): int(item["count"]) for item in statuses.to_dict("records")
            },
            "latest_action_timestamp": None if pd.isna(latest) else str(latest),
        }
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to read lifecycle summary: {exc}") from exc
