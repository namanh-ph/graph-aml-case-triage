"""Input readers for supervised AML model training."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.models.supervised_config import SupervisedModelConfig
from graph_aml.models.supervised_exceptions import SupervisedModelInputError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or int(limit) < 0:
        raise SupervisedModelInputError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object]) -> pd.DataFrame:
    safe_params = cast("dict[str, Any] | None", params or None)
    return pd.read_sql_query(text(sql), engine, params=safe_params)


def _dataset_reader(
    engine: Engine,
    table: str,
    id_column: str,
    dataset_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = f"SELECT * FROM {table}"
    if dataset_version:
        sql += " WHERE dataset_version = :dataset_version"
        params["dataset_version"] = dataset_version
    sql += f" ORDER BY label_timestamp ASC NULLS LAST, {id_column}"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise SupervisedModelInputError(f"failed to read {table}: {exc}") from exc


def read_case_supervised_training_dataset(
    engine: Engine,
    dataset_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read case-level supervised-readiness rows."""

    return _dataset_reader(
        engine,
        "mart.case_supervised_dataset",
        "case_id",
        dataset_version,
        limit,
    )


def read_account_supervised_training_dataset(
    engine: Engine,
    dataset_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read account-level supervised-readiness rows."""

    return _dataset_reader(
        engine,
        "mart.account_supervised_dataset",
        "account_id",
        dataset_version,
        limit,
    )


def read_supervised_training_dataset(
    engine: Engine,
    config: SupervisedModelConfig | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read the configured supervised-readiness training dataset."""

    resolved = config or SupervisedModelConfig()
    if resolved.dataset.level == "case":
        return read_case_supervised_training_dataset(
            engine,
            resolved.dataset.dataset_version,
            limit,
        )
    return read_account_supervised_training_dataset(
        engine,
        resolved.dataset.dataset_version,
        limit,
    )
