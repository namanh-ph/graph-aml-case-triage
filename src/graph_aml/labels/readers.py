"""Readback utilities for persisted analyst labels."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.labels.exceptions import LabelPersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise LabelPersistenceError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: Mapping[str, object] | None, name: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine, params=params)
    except Exception as exc:
        raise LabelPersistenceError(f"failed to read {name}: {exc}") from exc


def _label_reader(
    engine: Engine,
    table: str,
    version_column: str,
    version: str | None,
    label_column: str,
    label: int | None,
    limit: int | None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if version:
        clauses.append(f"{version_column} = :version")
        params["version"] = version
    if label is not None:
        if label not in {0, 1}:
            raise LabelPersistenceError("label filter must be 0 or 1")
        clauses.append(f"{label_column} = :label")
        params["label"] = label
    sql = f"SELECT * FROM {table}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY label_timestamp DESC, 1"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read(engine, sql, params, table)


def read_case_labels(
    engine: Engine,
    label_version: str | None = None,
    case_label: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    return _label_reader(
        engine,
        "aml.case_labels",
        "label_version",
        label_version,
        "case_label",
        case_label,
        limit,
    )


def read_account_labels(
    engine: Engine,
    label_version: str | None = None,
    account_label: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    return _label_reader(
        engine,
        "aml.account_labels",
        "label_version",
        label_version,
        "account_label",
        account_label,
        limit,
    )


def read_case_supervised_dataset(
    engine: Engine,
    dataset_version: str | None = None,
    case_label: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    return _label_reader(
        engine,
        "mart.case_supervised_dataset",
        "dataset_version",
        dataset_version,
        "case_label",
        case_label,
        limit,
    )


def read_account_supervised_dataset(
    engine: Engine,
    dataset_version: str | None = None,
    account_label: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    return _label_reader(
        engine,
        "mart.account_supervised_dataset",
        "dataset_version",
        dataset_version,
        "account_label",
        account_label,
        limit,
    )


def read_label_summary(engine: Engine) -> dict[str, object]:
    """Read compact persisted label summary counts."""

    try:
        case_labels = read_case_labels(engine)
        account_labels = read_account_labels(engine)
        case_dataset = read_case_supervised_dataset(engine)
        account_dataset = read_account_supervised_dataset(engine)
    except LabelPersistenceError:
        raise
    latest = None
    if "label_timestamp" in case_labels and not case_labels.empty:
        latest = str(pd.to_datetime(case_labels["label_timestamp"], errors="coerce").max())
    return {
        "case_label_count": int(len(case_labels)),
        "account_label_count": int(len(account_labels)),
        "case_dataset_count": int(len(case_dataset)),
        "account_dataset_count": int(len(account_dataset)),
        "positive_case_labels": (
            int((case_labels.get("case_label") == 1).sum()) if not case_labels.empty else 0
        ),
        "negative_case_labels": (
            int((case_labels.get("case_label") == 0).sum()) if not case_labels.empty else 0
        ),
        "latest_label_timestamp": latest,
    }
