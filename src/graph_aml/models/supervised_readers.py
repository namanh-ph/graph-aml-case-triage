"""Readback utilities for supervised AML model outputs."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.models.supervised_exceptions import SupervisedPersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or int(limit) < 0:
        raise SupervisedPersistenceError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object]) -> pd.DataFrame:
    safe_params = cast("dict[str, Any] | None", params or None)
    return pd.read_sql_query(text(sql), engine, params=safe_params)


def read_supervised_model_scores(
    engine: Engine,
    entity_level: str | None = None,
    model_version: str | None = None,
    dataset_version: str | None = None,
    predicted_label: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read supervised model scores."""

    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    for column, value in (
        ("entity_level", entity_level),
        ("model_version", model_version),
        ("dataset_version", dataset_version),
    ):
        if value:
            clauses.append(f"{column} = :{column}")
            params[column] = value
    if predicted_label is not None:
        clauses.append("predicted_label = :predicted_label")
        params["predicted_label"] = int(predicted_label)
    sql = "SELECT * FROM mart.supervised_model_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_rank ASC, supervised_score DESC, entity_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to read supervised scores: {exc}") from exc


def read_supervised_model_runs(
    engine: Engine,
    model_version: str | None = None,
    entity_level: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read supervised model run metadata."""

    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if entity_level:
        clauses.append("entity_level = :entity_level")
        params["entity_level"] = entity_level
    sql = "SELECT * FROM governance.supervised_model_runs"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY trained_at DESC NULLS LAST, run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to read supervised runs: {exc}") from exc


def read_supervised_model_summary(engine: Engine) -> dict[str, object]:
    """Read compact supervised model summary."""

    try:
        scores = read_supervised_model_scores(engine, limit=None)
        runs = read_supervised_model_runs(engine, limit=None)
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to summarise supervised outputs: {exc}") from exc
    latest_version = None if runs.empty else str(runs.iloc[0].get("model_version"))
    latest_trained = None if runs.empty else str(runs.iloc[0].get("trained_at"))
    return {
        "score_row_count": int(len(scores)),
        "model_run_count": int(len(runs)),
        "latest_model_version": latest_version,
        "latest_trained_timestamp": latest_trained,
        "entity_level_counts": scores.get("entity_level", pd.Series(dtype=object))
        .dropna()
        .astype(str)
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict(),
        "predicted_label_counts": scores.get("predicted_label", pd.Series(dtype=object))
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict(),
    }
