"""Persist account-level features into PostgreSQL mart tables."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.features.account import (
    ACCOUNT_FEATURE_COLUMNS,
    AccountFeatureConfig,
)
from graph_aml.features.exceptions import FeaturePersistenceError

MART_ACCOUNT_FEATURE_TABLE = "mart.features_account_daily"

MART_ACCOUNT_FEATURE_COLUMNS = (
    "account_id",
    "feature_date",
    "feature_version",
    "txn_count_1d",
    "txn_count_7d",
    "total_sent_7d",
    "total_received_7d",
    "avg_txn_amount_30d",
    "max_txn_amount_30d",
    "unique_counterparties_7d",
    "in_out_ratio_7d",
    "retained_balance_proxy",
    "below_threshold_count_24h",
    "dormant_days_before_activity",
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
    "counterparty_entropy",
)

MART_ACCOUNT_FEATURE_CONFLICT_COLUMNS = (
    "account_id",
    "feature_date",
    "feature_version",
)
COUNT_COLUMNS = (
    "txn_count_1d",
    "txn_count_7d",
    "unique_counterparties_7d",
    "below_threshold_count_24h",
)
FLOAT_COLUMNS = (
    "total_sent_7d",
    "total_received_7d",
    "avg_txn_amount_30d",
    "max_txn_amount_30d",
    "in_out_ratio_7d",
    "retained_balance_proxy",
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
    "counterparty_entropy",
)
NON_NEGATIVE_FLOAT_COLUMNS = (
    "total_sent_7d",
    "total_received_7d",
    "avg_txn_amount_30d",
    "max_txn_amount_30d",
    "in_out_ratio_7d",
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
    "counterparty_entropy",
)
RATIO_BOUND_COLUMNS = (
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
)
IN_OUT_RATIO_CAP = 999999.0


def _require_columns(frame: pd.DataFrame) -> None:
    missing = set(MART_ACCOUNT_FEATURE_COLUMNS).difference(frame.columns)
    if missing:
        raise FeaturePersistenceError(
            f"account features are missing required columns: {sorted(missing)}"
        )


def _coerce_feature_dates(values: pd.Series) -> pd.Series:
    timestamps = pd.to_datetime(values, utc=True, errors="coerce")
    if timestamps.isna().any():
        raise FeaturePersistenceError("feature_date contains invalid or missing values")
    return timestamps.dt.date


def _coerce_count_column(values: pd.Series, column: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0)
    if (numeric < 0).any() or (numeric % 1 != 0).any():
        raise FeaturePersistenceError(f"{column} must contain non-negative integers")
    return numeric.astype("int64")


def _coerce_float_column(values: pd.Series, column: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric.replace([float("inf"), -float("inf")], IN_OUT_RATIO_CAP)
    numeric = numeric.fillna(0.0)
    if column in NON_NEGATIVE_FLOAT_COLUMNS and (numeric < 0).any():
        raise FeaturePersistenceError(f"{column} must be non-negative")
    if column in RATIO_BOUND_COLUMNS and (numeric > 1).any():
        raise FeaturePersistenceError(f"{column} must be between 0.0 and 1.0")
    return numeric.astype("float64")


def _coerce_dormant_days(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    non_null = numeric.dropna()
    if (non_null < 0).any() or (non_null % 1 != 0).any():
        raise FeaturePersistenceError(
            "dormant_days_before_activity must be null or a non-negative integer"
        )
    return numeric.astype("Int64")


def prepare_account_features_for_persistence(features: pd.DataFrame) -> pd.DataFrame:
    """Coerce and validate account features before PostgreSQL upsert."""

    try:
        _require_columns(features)
        output = features.loc[:, MART_ACCOUNT_FEATURE_COLUMNS].copy()
        if output.empty:
            return output

        output["account_id"] = output["account_id"].astype("string").str.strip()
        output["feature_version"] = output["feature_version"].astype("string").str.strip()
        if output["account_id"].isna().any() or (output["account_id"] == "").any():
            raise FeaturePersistenceError("account_id must be non-null")
        if output["feature_version"].isna().any() or (output["feature_version"] == "").any():
            raise FeaturePersistenceError("feature_version must be non-null")

        output["feature_date"] = _coerce_feature_dates(output["feature_date"])
        for column in COUNT_COLUMNS:
            output[column] = _coerce_count_column(output[column], column)
        for column in FLOAT_COLUMNS:
            output[column] = _coerce_float_column(output[column], column)
        output["dormant_days_before_activity"] = _coerce_dormant_days(
            output["dormant_days_before_activity"]
        )

        duplicate_count = output.duplicated(
            subset=list(MART_ACCOUNT_FEATURE_CONFLICT_COLUMNS)
        ).sum()
        if duplicate_count:
            raise FeaturePersistenceError(
                "account_id, feature_date, and feature_version must be unique"
            )

        return output.reset_index(drop=True)
    except FeaturePersistenceError:
        raise
    except Exception as exc:
        raise FeaturePersistenceError(
            f"Failed to prepare account features for persistence: {exc}"
        ) from exc


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


def _upsert_sql(columns: tuple[str, ...]) -> str:
    insert_columns = ", ".join(columns)
    placeholders = ", ".join(f":{column}" for column in columns)
    conflict_columns = ", ".join(MART_ACCOUNT_FEATURE_CONFLICT_COLUMNS)
    update_columns = [
        column for column in columns if column not in MART_ACCOUNT_FEATURE_CONFLICT_COLUMNS
    ]
    update_clause = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return f"""
        INSERT INTO {MART_ACCOUNT_FEATURE_TABLE} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns}) DO UPDATE SET {update_clause}
    """


def upsert_account_features(
    engine: Engine,
    features: pd.DataFrame,
) -> int:
    """Upsert account features into mart.features_account_daily."""

    if features.empty:
        return 0
    prepared = prepare_account_features_for_persistence(features)
    if prepared.empty:
        return 0
    statement = text(_upsert_sql(MART_ACCOUNT_FEATURE_COLUMNS))
    try:
        with engine.begin() as connection:
            connection.execute(statement, _records(prepared))
    except Exception as exc:
        raise FeaturePersistenceError(f"Failed to upsert account features: {exc}") from exc
    return len(prepared)


def _feature_version_label(prepared: pd.DataFrame) -> str:
    versions = sorted(str(value) for value in prepared["feature_version"].dropna().unique())
    return ",".join(versions) if versions else "unknown"


def _persistence_summary(prepared: pd.DataFrame, row_count: int) -> dict[str, int]:
    if prepared.empty:
        return {
            "feature_rows_upserted": row_count,
            "account_count": 0,
            "feature_date_count": 0,
            "feature_version_count": 0,
        }
    return {
        "feature_rows_upserted": int(row_count),
        "account_count": int(prepared["account_id"].nunique(dropna=True)),
        "feature_date_count": int(prepared["feature_date"].nunique(dropna=True)),
        "feature_version_count": int(prepared["feature_version"].nunique(dropna=True)),
    }


def persist_account_features(
    engine: Engine,
    features: pd.DataFrame,
    write_audit: bool = True,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, int]:
    """Prepare, upsert, and optionally audit account feature persistence."""

    try:
        prepared = prepare_account_features_for_persistence(features)
        row_count = upsert_account_features(engine, prepared)
        summary = _persistence_summary(prepared, row_count)
        if write_audit:
            from graph_aml.features.audit import write_feature_persistence_audit_event

            write_feature_persistence_audit_event(
                engine,
                row_count=row_count,
                account_count=summary["account_count"],
                feature_date_count=summary["feature_date_count"],
                feature_version=_feature_version_label(prepared),
                status="completed",
                run_id=run_id,
                metadata=metadata,
            )
        return summary
    except FeaturePersistenceError:
        raise
    except Exception as exc:
        raise FeaturePersistenceError(f"Failed to persist account features: {exc}") from exc


def _base_features_with_mart_defaults(features: pd.DataFrame) -> pd.DataFrame:
    output = features.copy()
    defaults: dict[str, object] = {
        "retained_balance_proxy": 0.0,
        "below_threshold_count_24h": 0,
        "dormant_days_before_activity": pd.NA,
        "cross_border_ratio_30d": 0.0,
        "high_risk_country_exposure": 0.0,
        "counterparty_entropy": 0.0,
    }
    for column, value in defaults.items():
        if column not in output.columns:
            output[column] = value
    return output.loc[:, MART_ACCOUNT_FEATURE_COLUMNS]


def calculate_and_persist_account_features_from_staged(
    engine: Engine,
    config: AccountFeatureConfig | None = None,
    limit: int | None = None,
    extended: bool = True,
    write_audit: bool = True,
) -> dict[str, int]:
    """Calculate account features from staging tables and persist them to mart."""

    try:
        if extended:
            from graph_aml.features.staged import calculate_extended_account_features_from_staged

            features = calculate_extended_account_features_from_staged(
                engine,
                config=config,
                limit=limit,
            )
        else:
            from graph_aml.features.staged import calculate_account_features_from_staged

            features = calculate_account_features_from_staged(
                engine,
                config=config,
                limit=limit,
            )
            if set(ACCOUNT_FEATURE_COLUMNS).issubset(features.columns):
                features = _base_features_with_mart_defaults(features)
        return persist_account_features(
            engine,
            features,
            write_audit=write_audit,
            metadata={"limit": limit, "extended": extended},
        )
    except FeaturePersistenceError:
        raise
    except Exception as exc:
        raise FeaturePersistenceError(
            f"Failed to calculate and persist account features from staging: {exc}"
        ) from exc
