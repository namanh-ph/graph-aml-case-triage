"""Validation helpers for account risk scores."""

from __future__ import annotations

import json

import pandas as pd

from graph_aml.scoring.components import RISK_COMPONENT_COLUMNS
from graph_aml.scoring.composite import ACCOUNT_RISK_SCORE_COLUMNS
from graph_aml.scoring.exceptions import ScoringValidationError

PREPARED_ACCOUNT_RISK_SCORE_COLUMNS = (
    "account_id",
    "score_date",
    "score_name",
    "score_version",
    "account_risk_score",
    "risk_band",
    "risk_rank",
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
    "component_coverage",
    "alert_count",
    "high_severity_alert_count",
    "critical_severity_alert_count",
    "max_rule_alert_score",
    "mean_rule_alert_score",
    "max_anomaly_score",
    "graph_percentile_score",
    "weights",
    "metadata",
    "scored_at",
)

_SCORE_COLUMNS = (
    "account_risk_score",
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
    "max_rule_alert_score",
    "mean_rule_alert_score",
    "max_anomaly_score",
    "graph_percentile_score",
)


def _validate_common_account_ids(frame: pd.DataFrame) -> None:
    if "account_id" not in frame.columns:
        raise ScoringValidationError("frame must include account_id")
    if frame["account_id"].isna().any():
        raise ScoringValidationError("account_id values must be non-null")
    if frame["account_id"].duplicated().any():
        raise ScoringValidationError("account_id values must be unique")


def validate_risk_component_frame(components: pd.DataFrame) -> None:
    """Validate risk component rows."""

    missing = set(RISK_COMPONENT_COLUMNS).difference(components.columns)
    if missing:
        raise ScoringValidationError(f"components missing required columns: {sorted(missing)}")
    _validate_common_account_ids(components)
    for column in [c for c in RISK_COMPONENT_COLUMNS if c.endswith("_score")]:
        values = pd.to_numeric(components[column], errors="coerce")
        if values.isna().any() or (values < 0).any() or (values > 100).any():
            raise ScoringValidationError(f"{column} values must be in [0, 100]")


def validate_account_risk_score_frame(scores: pd.DataFrame) -> None:
    """Validate computed account risk score rows."""

    missing = set(ACCOUNT_RISK_SCORE_COLUMNS).difference(scores.columns)
    if missing:
        raise ScoringValidationError(f"scores missing required columns: {sorted(missing)}")
    _validate_common_account_ids(scores)
    for column in _SCORE_COLUMNS:
        values = pd.to_numeric(scores[column], errors="coerce")
        if values.isna().any() or (values < 0).any() or (values > 100).any():
            raise ScoringValidationError(f"{column} values must be in [0, 100]")
    invalid_bands = set(scores["risk_band"].astype(str)).difference(
        {"low", "medium", "high", "critical"}
    )
    if invalid_bands:
        raise ScoringValidationError(f"invalid risk bands: {sorted(invalid_bands)}")
    ranks = pd.to_numeric(scores["risk_rank"], errors="coerce")
    if ranks.isna().any() or (ranks < 1).any() or (ranks % 1 != 0).any():
        raise ScoringValidationError("risk_rank values must be positive integers")


def validate_prepared_account_risk_score_frame(prepared_scores: pd.DataFrame) -> None:
    """Validate account risk scores prepared for persistence."""

    missing = set(PREPARED_ACCOUNT_RISK_SCORE_COLUMNS).difference(prepared_scores.columns)
    if missing:
        raise ScoringValidationError(f"prepared scores missing required columns: {sorted(missing)}")
    validate_account_risk_score_frame(prepared_scores)
    for column in ("score_date", "score_name", "score_version", "scored_at"):
        if prepared_scores[column].isna().any():
            raise ScoringValidationError(f"{column} values must be non-null")


def build_account_risk_score_quality_summary(scores: pd.DataFrame) -> dict[str, object]:
    """Build JSON-serialisable score quality diagnostics."""

    if scores.empty:
        return {
            "row_count": 0,
            "unique_account_count": 0,
            "risk_band_counts": {},
            "min_score": None,
            "max_score": None,
            "mean_score": None,
            "component_coverage_mean": None,
            "missing_account_ids": 0,
            "duplicate_account_ids": 0,
        }
    score_values = pd.to_numeric(scores.get("account_risk_score"), errors="coerce")
    coverage = pd.to_numeric(scores.get("component_coverage"), errors="coerce")
    band_counts = (
        scores.get("risk_band", pd.Series(dtype="object")).astype(str).value_counts().sort_index()
    )
    return {
        "row_count": int(len(scores)),
        "unique_account_count": int(scores["account_id"].nunique(dropna=True))
        if "account_id" in scores
        else 0,
        "risk_band_counts": {str(key): int(value) for key, value in band_counts.to_dict().items()},
        "min_score": float(score_values.min()) if not score_values.empty else None,
        "max_score": float(score_values.max()) if not score_values.empty else None,
        "mean_score": float(score_values.mean()) if not score_values.empty else None,
        "component_coverage_mean": float(coverage.mean()) if not coverage.empty else None,
        "missing_account_ids": int(scores["account_id"].isna().sum())
        if "account_id" in scores
        else 0,
        "duplicate_account_ids": int(scores["account_id"].duplicated().sum())
        if "account_id" in scores
        else 0,
    }


def compare_account_risk_score_row_counts(
    source_scores: pd.DataFrame,
    persisted_scores: pd.DataFrame,
) -> dict[str, object]:
    """Compare source and persisted account risk score row counts."""

    source_count = int(len(source_scores))
    persisted_count = int(len(persisted_scores))
    warnings: list[str] = []
    if source_count != persisted_count:
        warnings.append(
            f"source row count {source_count} differs from persisted row count {persisted_count}"
        )
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }


def assert_json_serialisable(payload: object) -> None:
    """Internal helper used by tests and summary writers."""

    try:
        json.dumps(payload, default=str)
    except TypeError as exc:
        raise ScoringValidationError(f"payload is not JSON serialisable: {exc}") from exc
