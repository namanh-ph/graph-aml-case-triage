"""Audit event readers for dashboard governance pages."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.dashboard.exceptions import DashboardDataError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise DashboardDataError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(sql), engine, params=params or None)


def read_dashboard_audit_events(
    engine: Engine,
    components: tuple[str, ...] | list[str] | None = None,
    event_types: tuple[str, ...] | list[str] | None = None,
    statuses: tuple[str, ...] | list[str] | None = None,
    run_id: str | None = None,
    search_text: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if components:
        clauses.append("component = ANY(:components)")
        params["components"] = list(components)
    if event_types:
        clauses.append("event_type = ANY(:event_types)")
        params["event_types"] = list(event_types)
    if statuses:
        clauses.append("status = ANY(:statuses)")
        params["statuses"] = list(statuses)
    if run_id:
        clauses.append("run_id = :run_id")
        params["run_id"] = run_id
    if search_text:
        clauses.append(
            "("
            "event_type ILIKE :search_text OR component ILIKE :search_text OR "
            "action ILIKE :search_text OR status ILIKE :search_text OR "
            "run_id ILIKE :search_text OR details::text ILIKE :search_text"
            ")"
        )
        params["search_text"] = f"%{search_text}%"
    sql = "SELECT * FROM governance.audit_events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY event_timestamp DESC NULLS LAST, audit_event_id DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read audit events: {exc}") from exc


def read_dashboard_audit_filter_options(engine: Engine) -> dict[str, list[str]]:
    try:
        components = _read(
            engine,
            "SELECT DISTINCT component FROM governance.audit_events ORDER BY component",
        )
        event_types = _read(
            engine,
            "SELECT DISTINCT event_type FROM governance.audit_events ORDER BY event_type",
        )
        statuses = _read(
            engine,
            "SELECT DISTINCT status FROM governance.audit_events ORDER BY status",
        )
        return {
            "components": components.get(
                "component",
                pd.Series(dtype=str),
            ).dropna().astype(str).tolist(),
            "event_types": event_types.get(
                "event_type",
                pd.Series(dtype=str),
            ).dropna().astype(str).tolist(),
            "statuses": statuses.get("status", pd.Series(dtype=str)).dropna().astype(str).tolist(),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to read audit filter options: {exc}") from exc


def read_dashboard_audit_summary(engine: Engine) -> dict[str, object]:
    try:
        events = read_dashboard_audit_events(engine, limit=None)
        return {
            "event_count": int(len(events)),
            "component_counts": events.get(
                "component",
                pd.Series(dtype=str),
            ).value_counts().to_dict(),
            "event_type_counts": events.get(
                "event_type",
                pd.Series(dtype=str),
            ).value_counts().to_dict(),
            "status_counts": events.get("status", pd.Series(dtype=str)).value_counts().to_dict(),
            "latest_event_timestamp": None
            if events.empty or "event_timestamp" not in events
            else str(events["event_timestamp"].max()),
        }
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to build audit summary: {exc}") from exc
