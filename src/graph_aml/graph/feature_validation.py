"""Validation helpers for persisted graph analytics features."""

from __future__ import annotations

import pandas as pd

from graph_aml.graph.analytics import GRAPH_ANALYTICS_FEATURE_COLUMNS
from graph_aml.graph.exceptions import GraphFeatureValidationError

GRAPH_FEATURE_REQUIRED_METADATA_COLUMNS = (
    "feature_date",
    "feature_version",
    "graph_build_id",
    "graph_database",
    "computed_at",
    "metadata",
)

_NUMERIC_FEATURE_COLUMNS = tuple(
    column
    for column in GRAPH_ANALYTICS_FEATURE_COLUMNS
    if column not in {"account_id", "shortest_path_to_flagged"}
)


def _missing_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return sorted(set(columns).difference(frame.columns))


def validate_graph_feature_frame(features: pd.DataFrame) -> None:
    """Validate the account-level graph analytics feature frame."""

    if not isinstance(features, pd.DataFrame):
        raise GraphFeatureValidationError("features must be a DataFrame")
    missing = _missing_columns(features, GRAPH_ANALYTICS_FEATURE_COLUMNS)
    if missing:
        raise GraphFeatureValidationError(f"graph features are missing columns: {missing}")
    if features.empty:
        return
    account_ids = features["account_id"].astype("string").str.strip()
    if account_ids.isna().any() or (account_ids == "").any():
        raise GraphFeatureValidationError("account_id must be non-null")
    if account_ids.duplicated().any():
        raise GraphFeatureValidationError("account_id values must be unique")


def validate_prepared_graph_feature_frame(prepared_features: pd.DataFrame) -> None:
    """Validate a graph feature frame after persistence metadata has been attached."""

    validate_graph_feature_frame(prepared_features)
    missing = _missing_columns(prepared_features, GRAPH_FEATURE_REQUIRED_METADATA_COLUMNS)
    if missing:
        raise GraphFeatureValidationError(
            f"prepared graph features are missing metadata columns: {missing}"
        )
    if prepared_features.empty:
        return
    for column in _NUMERIC_FEATURE_COLUMNS:
        if prepared_features[column].isna().any():
            raise GraphFeatureValidationError(f"{column} must be non-null after preparation")
    for column in ("feature_date", "feature_version", "graph_build_id", "computed_at"):
        if prepared_features[column].isna().any():
            raise GraphFeatureValidationError(f"{column} must be non-null")


def compare_graph_feature_row_counts(
    source_features: pd.DataFrame,
    persisted_features: pd.DataFrame,
) -> dict[str, object]:
    """Compare source and persisted graph feature row counts."""

    source_count = int(len(source_features))
    persisted_count = int(len(persisted_features))
    warnings: list[str] = []
    if source_count != persisted_count:
        warnings.append(
            f"source row count {source_count} does not match persisted row count {persisted_count}"
        )
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }


def build_graph_feature_quality_summary(features: pd.DataFrame) -> dict[str, object]:
    """Build JSON-safe graph feature quality diagnostics."""

    if not isinstance(features, pd.DataFrame):
        raise GraphFeatureValidationError("features must be a DataFrame")
    missing_account_ids = 0
    duplicate_account_ids = 0
    if "account_id" in features.columns and not features.empty:
        account_ids = features["account_id"].astype("string").str.strip()
        missing_account_ids = int((account_ids.isna() | (account_ids == "")).sum())
        duplicate_account_ids = int(account_ids.duplicated().sum())
    numeric_null_counts = {
        column: int(features[column].isna().sum())
        for column in _NUMERIC_FEATURE_COLUMNS
        if column in features.columns
    }

    def nonzero(column: str) -> int:
        if column not in features.columns:
            return 0
        numeric = pd.to_numeric(features[column], errors="coerce").fillna(0)
        return int((numeric != 0).sum())

    return {
        "row_count": int(len(features)),
        "unique_account_count": int(features["account_id"].nunique())
        if "account_id" in features
        else 0,
        "missing_account_ids": missing_account_ids,
        "duplicate_account_ids": duplicate_account_ids,
        "numeric_null_counts": numeric_null_counts,
        "nonzero_feature_counts": {
            "pagerank_score": nonzero("pagerank_score"),
            "cycle_count": nonzero("cycle_count"),
            "alert_count": nonzero("alert_count"),
            "fan_in_count": nonzero("fan_in_count"),
            "fan_out_count": nonzero("fan_out_count"),
        },
    }
