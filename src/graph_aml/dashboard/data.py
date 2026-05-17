"""PostgreSQL readers for the local Streamlit dashboard."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.dashboard.exceptions import DashboardDataError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise DashboardDataError("limit must be non-negative")
    return int(limit)


def _normalise_values(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _id_filter(
    column: str,
    param_name: str,
    values: Sequence[str] | None,
) -> tuple[str | None, dict[str, object]]:
    clean = _normalise_values(values)
    if not clean:
        return None, {}
    return f"{column} = ANY(:{param_name})", {param_name: clean}


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(sql), engine, params=params or None)


def _count_query(engine: Engine, sql: str) -> int:
    frame = _read(engine, sql)
    if frame.empty:
        return 0
    return int(frame.iloc[0, 0] or 0)


def _distribution(engine: Engine, sql: str, key: str, value: str = "row_count") -> dict[str, int]:
    frame = _read(engine, sql)
    return {str(row[key]): int(row[value]) for row in frame.to_dict("records")}


def read_dashboard_overview_counts(engine: Engine) -> dict[str, object]:
    """Read high-level dashboard counts and simple distributions."""

    try:
        return {
            "transaction_count": _count_query(engine, "SELECT COUNT(*) FROM staging.transactions"),
            "account_count": _count_query(engine, "SELECT COUNT(*) FROM staging.accounts"),
            "alert_count": _count_query(engine, "SELECT COUNT(*) FROM aml.alerts"),
            "case_count": _count_query(engine, "SELECT COUNT(*) FROM aml.cases"),
            "case_risk_score_count": _count_query(
                engine, "SELECT COUNT(*) FROM aml.case_risk_scores"
            ),
            "lifecycle_event_count": _count_query(
                engine, "SELECT COUNT(*) FROM aml.case_lifecycle_events"
            ),
            "case_status_counts": _distribution(
                engine,
                """
                    SELECT status, COUNT(*) AS row_count
                    FROM aml.cases
                    GROUP BY status
                    ORDER BY status
                """,
                "status",
            ),
            "case_risk_band_counts": _distribution(
                engine,
                """
                    SELECT risk_band, COUNT(*) AS row_count
                    FROM aml.case_risk_scores
                    GROUP BY risk_band
                    ORDER BY risk_band
                """,
                "risk_band",
            ),
            "alert_severity_counts": _distribution(
                engine,
                """
                    SELECT severity, COUNT(*) AS row_count
                    FROM aml.alerts
                    GROUP BY severity
                    ORDER BY severity
                """,
                "severity",
            ),
            "alert_typology_counts": _distribution(
                engine,
                """
                    SELECT typology, COUNT(*) AS row_count
                    FROM aml.alerts
                    GROUP BY typology
                    ORDER BY typology
                """,
                "typology",
            ),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard overview counts: {exc}") from exc


def read_dashboard_alert_queue(
    engine: Engine,
    severities: tuple[str, ...] | list[str] | None = None,
    typologies: tuple[str, ...] | list[str] | None = None,
    account_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    for column, param_name, values in (
        ("severity", "severities", severities),
        ("typology", "typologies", typologies),
    ):
        clause, id_params = _id_filter(column, param_name, values)
        if clause:
            clauses.append(clause)
            params.update(id_params)
    if account_id:
        clauses.append("account_id ILIKE :account_id")
        params["account_id"] = f"%{account_id.strip()}%"
    sql = "SELECT * FROM aml.alerts"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_score_rule DESC NULLS LAST, created_at DESC NULLS LAST, alert_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard alert queue: {exc}") from exc


def read_dashboard_case_queue(
    engine: Engine,
    statuses: tuple[str, ...] | list[str] | None = None,
    risk_bands: tuple[str, ...] | list[str] | None = None,
    assigned_to: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    clause, id_params = _id_filter("c.status", "statuses", statuses)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    clause, id_params = _id_filter("rs.risk_band", "risk_bands", risk_bands)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    if assigned_to:
        clauses.append("c.assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to
    sql = """
        WITH latest_scores AS (
            SELECT DISTINCT ON (case_id) *
            FROM aml.case_risk_scores
            ORDER BY case_id, scored_at DESC NULLS LAST, case_risk_score DESC NULLS LAST
        )
        SELECT
            c.*,
            rs.case_risk_score,
            rs.risk_band,
            rs.risk_rank,
            rs.scored_at AS risk_scored_at
        FROM aml.cases c
        LEFT JOIN latest_scores rs ON c.case_id = rs.case_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += """
        ORDER BY rs.risk_rank ASC NULLS LAST,
                 rs.case_risk_score DESC NULLS LAST,
                 c.priority_score DESC NULLS LAST,
                 c.case_id
    """
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard case queue: {exc}") from exc


def read_dashboard_lifecycle_events(
    engine: Engine,
    case_id: str,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    if not case_id.strip():
        raise DashboardDataError("case_id must be non-empty")
    params: dict[str, object] = {"case_id": case_id}
    sql = """
        SELECT *
        FROM aml.case_lifecycle_events
        WHERE case_id = :case_id
        ORDER BY action_timestamp DESC, action_id
    """
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read lifecycle events: {exc}") from exc


def read_dashboard_case_detail(engine: Engine, case_id: str) -> dict[str, pd.DataFrame]:
    if not case_id.strip():
        raise DashboardDataError("case_id must be non-empty")
    try:
        params: dict[str, object] = {"case_id": case_id}
        case = _read(engine, "SELECT * FROM aml.cases WHERE case_id = :case_id", params)
        case_risk_scores = _read(
            engine,
            """
                SELECT *
                FROM aml.case_risk_scores
                WHERE case_id = :case_id
                ORDER BY scored_at DESC NULLS LAST, case_risk_score DESC NULLS LAST
            """,
            params,
        )
        case_alerts = _read(
            engine,
            "SELECT * FROM aml.case_alerts WHERE case_id = :case_id ORDER BY alert_id",
            params,
        )
        alert_ids = (
            tuple(case_alerts["alert_id"].dropna().astype(str))
            if "alert_id" in case_alerts
            else ()
        )
        alerts = pd.DataFrame()
        if alert_ids:
            alerts = _read(
                engine,
                """
                    SELECT *
                    FROM aml.alerts
                    WHERE alert_id = ANY(:alert_ids)
                    ORDER BY risk_score_rule DESC NULLS LAST, created_at DESC NULLS LAST, alert_id
                """,
                {"alert_ids": list(alert_ids)},
            )
        case_entities = _read(
            engine,
            """
                SELECT *
                FROM aml.case_entities
                WHERE case_id = :case_id
                ORDER BY entity_type, entity_id
            """,
            params,
        )
        return {
            "case": case,
            "case_risk_scores": case_risk_scores,
            "case_alerts": case_alerts,
            "alerts": alerts,
            "case_entities": case_entities,
            "lifecycle_events": read_dashboard_lifecycle_events(engine, case_id),
        }
    except DashboardDataError:
        raise
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard case detail: {exc}") from exc


def read_dashboard_case_evidence(engine: Engine, case_id: str) -> dict[str, pd.DataFrame]:
    if not case_id.strip():
        raise DashboardDataError("case_id must be non-empty")
    try:
        params: dict[str, object] = {"case_id": case_id}
        evidence_packs = _read(
            engine,
            """
                SELECT *
                FROM aml.case_evidence_packs
                WHERE case_id = :case_id
                ORDER BY created_at DESC NULLS LAST, evidence_version
            """,
            params,
        )
        explanations = _read(
            engine,
            """
                SELECT *
                FROM aml.case_explanations
                WHERE case_id = :case_id
                ORDER BY created_at DESC NULLS LAST, explanation_version
            """,
            params,
        )
        return {"evidence_packs": evidence_packs, "explanations": explanations}
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard case evidence: {exc}") from exc


def _distinct_list(engine: Engine, sql: str, column: str) -> list[str]:
    frame = _read(engine, sql)
    if column not in frame:
        return []
    return sorted(str(value) for value in frame[column].dropna().unique() if str(value).strip())


def read_dashboard_filter_options(engine: Engine) -> dict[str, list[str]]:
    """Read filter choices for dashboard pages."""

    try:
        return {
            "alert_severities": _distinct_list(
                engine, "SELECT DISTINCT severity FROM aml.alerts ORDER BY severity", "severity"
            ),
            "alert_typologies": _distinct_list(
                engine, "SELECT DISTINCT typology FROM aml.alerts ORDER BY typology", "typology"
            ),
            "case_statuses": _distinct_list(
                engine, "SELECT DISTINCT status FROM aml.cases ORDER BY status", "status"
            ),
            "case_risk_bands": _distinct_list(
                engine,
                "SELECT DISTINCT risk_band FROM aml.case_risk_scores ORDER BY risk_band",
                "risk_band",
            ),
            "assigned_to": _distinct_list(
                engine,
                """
                    SELECT DISTINCT assigned_to
                    FROM aml.cases
                    WHERE assigned_to IS NOT NULL
                    ORDER BY assigned_to
                """,
                "assigned_to",
            ),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to read dashboard filter options: {exc}") from exc
