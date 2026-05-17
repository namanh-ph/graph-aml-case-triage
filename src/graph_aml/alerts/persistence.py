"""Persistence utilities for AML alerts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.alerts.dataframe import alerts_to_dataframe, normalise_alert_dataframe
from graph_aml.alerts.exceptions import AlertPersistenceError
from graph_aml.alerts.schema import ALERT_COLUMNS, AlertRecord
from graph_aml.alerts.summary import summarise_alerts

AML_ALERTS_TABLE = "aml.alerts"
ALERT_CONFLICT_COLUMNS = ("alert_id",)


def prepare_alerts_for_persistence(
    alerts: pd.DataFrame | tuple[AlertRecord, ...] | list[AlertRecord],
) -> pd.DataFrame:
    """Validate alerts and return a mart-compatible DataFrame."""

    try:
        if isinstance(alerts, pd.DataFrame):
            if alerts.empty:
                return pd.DataFrame(columns=ALERT_COLUMNS)
            frame = normalise_alert_dataframe(alerts)
        else:
            if len(alerts) == 0:
                return pd.DataFrame(columns=ALERT_COLUMNS)
            frame = alerts_to_dataframe(alerts)
        output = frame.loc[:, ALERT_COLUMNS].copy()
        output["evidence_ids"] = output["evidence_ids"].apply(
            lambda values: list(values) if isinstance(values, tuple | list) else [str(values)]
        )
        return output
    except Exception as exc:
        raise AlertPersistenceError(f"Failed to prepare alerts for persistence: {exc}") from exc


def upsert_alerts(
    engine: Engine,
    alerts: pd.DataFrame | tuple[AlertRecord, ...] | list[AlertRecord],
) -> int:
    """Upsert alerts into aml.alerts using alert_id as the conflict key."""

    prepared = prepare_alerts_for_persistence(alerts)
    if prepared.empty:
        return 0
    statement = text(_upsert_sql(ALERT_COLUMNS))
    try:
        with engine.begin() as connection:
            connection.execute(statement, _records(prepared))
    except Exception as exc:
        raise AlertPersistenceError(f"Failed to upsert alerts: {exc}") from exc
    return len(prepared)


def persist_alerts(
    engine: Engine,
    alerts: pd.DataFrame | tuple[AlertRecord, ...] | list[AlertRecord],
    write_audit: bool = True,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, int]:
    """Prepare, upsert, and optionally audit AML alert persistence."""

    try:
        prepared = prepare_alerts_for_persistence(alerts)
        row_count = upsert_alerts(engine, prepared)
        summary_payload = summarise_alerts(prepared)
        summary = {
            "alerts_upserted": int(row_count),
            "unique_account_count": int(cast(Any, summary_payload["unique_account_count"])),
            "unique_rule_count": len(cast(dict[str, int], summary_payload["rule_name_counts"])),
            "unique_typology_count": len(cast(dict[str, int], summary_payload["typology_counts"])),
        }
        if write_audit:
            from graph_aml.alerts.audit import write_alert_persistence_audit_event

            write_alert_persistence_audit_event(
                engine,
                alert_count=row_count,
                rule_name_counts=cast(dict[str, int], summary_payload["rule_name_counts"]),
                severity_counts=cast(dict[str, int], summary_payload["severity_counts"]),
                status="completed",
                run_id=run_id,
                metadata=metadata,
            )
        return summary
    except AlertPersistenceError:
        raise
    except Exception as exc:
        raise AlertPersistenceError(f"Failed to persist alerts: {exc}") from exc


def read_alerts(
    engine: Engine,
    rule_name: str | None = None,
    severity: str | None = None,
    alert_status: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read persisted alerts with optional filters."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if rule_name is not None:
        clauses.append("rule_name = :rule_name")
        params["rule_name"] = rule_name
    if severity is not None:
        clauses.append("severity = :severity")
        params["severity"] = severity.lower()
    if alert_status is not None:
        clauses.append("alert_status = :alert_status")
        params["alert_status"] = alert_status

    sql = f"SELECT * FROM {AML_ALERTS_TABLE}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at, alert_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise AlertPersistenceError(f"Failed to read alerts: {exc}") from exc


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise AlertPersistenceError("limit must be non-negative")
    return int(limit)


def _upsert_sql(columns: tuple[str, ...]) -> str:
    insert_columns = ", ".join(columns)
    placeholders = ", ".join(f":{column}" for column in columns)
    update_columns = [column for column in columns if column not in ALERT_CONFLICT_COLUMNS]
    update_clause = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return f"""
        INSERT INTO {AML_ALERTS_TABLE} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT (alert_id) DO UPDATE SET {update_clause}
    """


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _to_db_value(value: object) -> object:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime | date):
        return value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "item"):
        try:
            item_value: object = value.item()
            return item_value
        except (AttributeError, ValueError):
            return str(value)
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {str(column): _to_db_value(value) for column, value in row.items()}
        for row in frame.astype(object).to_dict(orient="records")
    ]
