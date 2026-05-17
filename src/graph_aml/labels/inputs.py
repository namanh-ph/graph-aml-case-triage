"""PostgreSQL readers for analyst label inputs."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.labels.config import AnalystLabelConfig
from graph_aml.labels.exceptions import LabelInputError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise LabelInputError("limit must be non-negative")
    return int(limit)


def _id_filter(
    column: str,
    param_name: str,
    values: tuple[str, ...] | list[str] | None,
) -> tuple[str | None, dict[str, object]]:
    if not values:
        return None, {}
    clean = [str(value).strip() for value in values if str(value).strip()]
    if not clean:
        return None, {}
    return f"{column} = ANY(:{param_name})", {param_name: clean}


def _read_query(
    engine: Engine,
    sql: str,
    params: Mapping[str, object] | None,
    label: str,
) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine, params=params)
    except Exception as exc:
        raise LabelInputError(f"failed to read {label}: {exc}") from exc


def read_label_cases(
    engine: Engine,
    case_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM aml.cases"
    if case_version:
        sql += " WHERE case_version = :case_version"
        params["case_version"] = case_version
    sql += " ORDER BY case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "cases")


def read_label_lifecycle_events(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("case_id", "case_ids", case_ids)
    sql = "SELECT * FROM aml.case_lifecycle_events"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY case_id, action_timestamp DESC, action_id DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "case lifecycle events")


def read_label_case_entities(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("case_id", "case_ids", case_ids)
    sql = "SELECT * FROM aml.case_entities"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY case_id, entity_type, entity_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "case entities")


def read_label_case_risk_scores(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("case_id", "case_ids", case_ids)
    sql = "SELECT * FROM aml.case_risk_scores"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY case_id, scored_at DESC NULLS LAST, risk_rank"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "case risk scores")


def read_label_account_features(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.features_account_daily"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, feature_date DESC, feature_version"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "account features")


def read_label_account_risk_scores(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.account_risk_scores"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, score_date DESC, account_risk_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "account risk scores")


def read_label_graph_features(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.graph_features"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, computed_at DESC NULLS LAST, feature_date DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "graph features")


def read_label_anomaly_scores(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.account_anomaly_scores"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, score_date DESC, anomaly_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "anomaly scores")


def read_label_inputs(
    engine: Engine,
    config: AnalystLabelConfig | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read all input frames for analyst label generation."""

    _ = config or AnalystLabelConfig()
    cases = read_label_cases(engine, limit=limit)
    case_ids = tuple(cases["case_id"].dropna().astype(str)) if "case_id" in cases else ()
    lifecycle_events = read_label_lifecycle_events(engine, case_ids=case_ids, limit=limit)
    case_entities = read_label_case_entities(engine, case_ids=case_ids, limit=limit)
    case_risk_scores = read_label_case_risk_scores(engine, case_ids=case_ids, limit=limit)
    account_values: set[str] = set()
    if "primary_account_id" in cases:
        account_values.update(cases["primary_account_id"].dropna().astype(str))
    if {"entity_type", "entity_id"}.issubset(case_entities.columns):
        mask = case_entities["entity_type"].astype(str).str.lower().eq("account")
        account_values.update(case_entities.loc[mask, "entity_id"].dropna().astype(str))
    account_ids = tuple(sorted(account_values))
    return {
        "cases": cases,
        "lifecycle_events": lifecycle_events,
        "case_entities": case_entities,
        "case_risk_scores": case_risk_scores,
        "account_features": read_label_account_features(engine, account_ids, limit),
        "account_risk_scores": read_label_account_risk_scores(engine, account_ids, limit),
        "graph_features": read_label_graph_features(engine, account_ids, limit),
        "anomaly_scores": read_label_anomaly_scores(engine, account_ids, limit),
    }
