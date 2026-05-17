"""Validation helpers for analyst label datasets."""

from __future__ import annotations

import pandas as pd

from graph_aml.labels.config import AnalystLabelConfig
from graph_aml.labels.dataset import LabelDatasetBuildResult
from graph_aml.labels.exceptions import LabelValidationError
from graph_aml.labels.mapping import ACCOUNT_LABEL_COLUMNS, CASE_LABEL_COLUMNS
from graph_aml.labels.summary import label_dataset_result_to_dict


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise LabelValidationError(f"{name} missing columns: {sorted(missing)}")


def validate_case_labels(case_labels: pd.DataFrame) -> None:
    _require_columns(case_labels, CASE_LABEL_COLUMNS, "case_labels")
    if case_labels.empty:
        return
    if not set(case_labels["case_label"].dropna().astype(int)).issubset({0, 1}):
        raise LabelValidationError("case labels must be 0 or 1")
    if case_labels.duplicated(["case_id", "label_version"]).any():
        raise LabelValidationError("duplicate case labels")
    if case_labels["label_timestamp"].isna().any():
        raise LabelValidationError("case label timestamps are required")


def validate_account_labels(account_labels: pd.DataFrame) -> None:
    _require_columns(account_labels, ACCOUNT_LABEL_COLUMNS, "account_labels")
    if account_labels.empty:
        return
    if not set(account_labels["account_label"].dropna().astype(int)).issubset({0, 1}):
        raise LabelValidationError("account labels must be 0 or 1")
    if account_labels.duplicated(["account_id", "label_version"]).any():
        raise LabelValidationError("duplicate account labels")
    if account_labels["label_timestamp"].isna().any():
        raise LabelValidationError("account label timestamps are required")


def validate_label_dataset_result(
    result: LabelDatasetBuildResult,
    config: AnalystLabelConfig | None = None,
) -> None:
    resolved = config or AnalystLabelConfig()
    validate_case_labels(result.case_labels)
    validate_account_labels(result.account_labels)
    case_count = len(result.case_labels)
    positive_count = int((result.case_labels.get("case_label") == 1).sum()) if case_count else 0
    negative_count = int((result.case_labels.get("case_label") == 0).sum()) if case_count else 0
    if case_count < resolved.label_quality.min_case_labels:
        raise LabelValidationError("case label count below threshold")
    if positive_count < resolved.label_quality.min_positive_labels:
        raise LabelValidationError("positive label count below threshold")
    if negative_count < resolved.label_quality.min_negative_labels:
        raise LabelValidationError("negative label count below threshold")
    if (
        not resolved.label_quality.allow_single_class_dataset
        and positive_count * negative_count == 0
    ):
        raise LabelValidationError("single-class label datasets are disabled")


def build_label_quality_summary(
    result: LabelDatasetBuildResult,
    config: AnalystLabelConfig | None = None,
) -> dict[str, object]:
    resolved = config or AnalystLabelConfig()
    summary = label_dataset_result_to_dict(result)
    thresholds = {
        "min_case_labels": resolved.label_quality.min_case_labels,
        "min_positive_labels": resolved.label_quality.min_positive_labels,
        "min_negative_labels": resolved.label_quality.min_negative_labels,
        "allow_single_class_dataset": resolved.label_quality.allow_single_class_dataset,
    }
    summary["thresholds"] = thresholds
    summary["status"] = "ok"
    try:
        validate_label_dataset_result(result, resolved)
    except LabelValidationError as exc:
        summary["status"] = "warning"
        summary["warning"] = str(exc)
    return summary


def compare_label_row_counts(
    source: pd.DataFrame,
    persisted: pd.DataFrame,
) -> dict[str, object]:
    source_count = int(len(source))
    persisted_count = int(len(persisted))
    warnings = [] if source_count == persisted_count else ["row counts differ"]
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }
