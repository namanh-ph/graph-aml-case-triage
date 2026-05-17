"""Validation helpers for case-level risk scoring outputs."""

from __future__ import annotations

import json

import pandas as pd

from graph_aml.cases.exceptions import CaseRiskValidationError
from graph_aml.cases.risk_components import CASE_RISK_COMPONENT_COLUMNS
from graph_aml.cases.risk_scoring import CASE_RISK_SCORE_COLUMNS

CASE_RISK_PERSISTENCE_COLUMNS = CASE_RISK_SCORE_COLUMNS + (
    "weights",
    "metadata",
    "scored_at",
)


def _missing(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column not in frame.columns]


def _validate_scores(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            if values.isna().any() or ((values < 0) | (values > 100)).any():
                raise CaseRiskValidationError(f"{column} must be in [0, 100]")


def validate_case_risk_component_frame(components: pd.DataFrame) -> None:
    missing = _missing(components, CASE_RISK_COMPONENT_COLUMNS)
    if missing:
        raise CaseRiskValidationError(f"case risk components missing columns: {missing}")
    if not components.empty and components["case_id"].isna().any():
        raise CaseRiskValidationError("case_id cannot be null")
    score_columns = tuple(
        column for column in CASE_RISK_COMPONENT_COLUMNS if column.endswith("_score")
    )
    _validate_scores(components, score_columns + ("component_coverage",))


def validate_case_risk_score_frame(scores: pd.DataFrame) -> None:
    missing = _missing(scores, CASE_RISK_SCORE_COLUMNS)
    if missing:
        raise CaseRiskValidationError(f"case risk scores missing columns: {missing}")
    if not scores.empty:
        if scores["case_id"].isna().any():
            raise CaseRiskValidationError("case_id cannot be null")
        if scores["case_id"].duplicated().any():
            raise CaseRiskValidationError("case_id must be unique")
        if not scores["risk_band"].isin(("low", "medium", "high", "critical")).all():
            raise CaseRiskValidationError("risk_band is invalid")
        ranks = pd.to_numeric(scores["risk_rank"], errors="coerce")
        if ranks.isna().any() or (ranks < 1).any():
            raise CaseRiskValidationError("risk_rank must be positive")
    score_columns = tuple(column for column in CASE_RISK_SCORE_COLUMNS if column.endswith("_score"))
    _validate_scores(scores, score_columns + ("component_coverage",))


def validate_prepared_case_risk_score_frame(prepared_scores: pd.DataFrame) -> None:
    missing = _missing(prepared_scores, CASE_RISK_PERSISTENCE_COLUMNS)
    if missing:
        raise CaseRiskValidationError(f"prepared case risk scores missing columns: {missing}")
    validate_case_risk_score_frame(prepared_scores.loc[:, CASE_RISK_SCORE_COLUMNS])
    if "metadata" not in prepared_scores.columns or "weights" not in prepared_scores.columns:
        raise CaseRiskValidationError("prepared scores must include metadata and weights")


def build_case_risk_score_quality_summary(scores: pd.DataFrame) -> dict[str, object]:
    if scores.empty:
        return {
            "row_count": 0,
            "unique_case_count": 0,
            "risk_band_counts": {},
            "min_score": 0.0,
            "max_score": 0.0,
            "mean_score": 0.0,
            "component_coverage_mean": 0.0,
            "missing_case_ids": 0,
            "duplicate_case_ids": 0,
        }
    case_scores = pd.to_numeric(scores["case_risk_score"], errors="coerce").fillna(0)
    coverage = pd.to_numeric(scores["component_coverage"], errors="coerce").fillna(0)
    return {
        "row_count": int(len(scores)),
        "unique_case_count": int(scores["case_id"].nunique(dropna=True)),
        "risk_band_counts": {
            str(key): int(value)
            for key, value in scores["risk_band"].astype(str).value_counts().sort_index().items()
        },
        "min_score": float(case_scores.min()),
        "max_score": float(case_scores.max()),
        "mean_score": float(case_scores.mean()),
        "component_coverage_mean": float(coverage.mean()),
        "missing_case_ids": int(scores["case_id"].isna().sum()),
        "duplicate_case_ids": int(scores["case_id"].duplicated().sum()),
    }


def compare_case_risk_score_row_counts(
    source_scores: pd.DataFrame,
    persisted_scores: pd.DataFrame,
) -> dict[str, object]:
    warnings: list[str] = []
    source_count = int(len(source_scores))
    persisted_count = int(len(persisted_scores))
    if source_count != persisted_count:
        warnings.append("source and persisted case risk row counts differ")
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }


def assert_case_risk_summary_serialisable(payload: dict[str, object]) -> None:
    try:
        json.dumps(payload, sort_keys=True, default=str)
    except TypeError as exc:
        raise CaseRiskValidationError(f"payload is not JSON serialisable: {exc}") from exc
