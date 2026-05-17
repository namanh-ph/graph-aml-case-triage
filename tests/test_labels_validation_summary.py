from __future__ import annotations

import json

import pandas as pd
import pytest

from graph_aml.labels import (
    LabelDatasetBuildResult,
    LabelValidationError,
    build_label_quality_summary,
    compare_label_row_counts,
    validate_account_labels,
    validate_case_labels,
    validate_label_dataset_result,
)


def _case_labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1"],
            "label_version": ["v1"],
            "case_label": [1],
            "label_name": ["suspicious"],
            "source_status": ["Closed suspicious"],
            "source_action_type": ["close_suspicious"],
            "analyst_id": ["u1"],
            "decision_reason": ["reason"],
            "comment": ["comment"],
            "label_timestamp": [pd.Timestamp("2026-01-01")],
            "case_created_at": [pd.Timestamp("2025-12-31")],
            "case_updated_at": [pd.Timestamp("2026-01-01")],
            "metadata": [{}],
        }
    )


def _account_labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1"],
            "label_version": ["v1"],
            "account_label": [1],
            "label_name": ["suspicious"],
            "source_case_ids": [["C1"]],
            "source_case_labels": [[1]],
            "label_timestamp": [pd.Timestamp("2026-01-01")],
            "metadata": [{}],
        }
    )


def _result() -> LabelDatasetBuildResult:
    return LabelDatasetBuildResult(
        case_labels=_case_labels(),
        account_labels=_account_labels(),
        case_dataset=pd.DataFrame(
            {"case_label": [1], "label_timestamp": [pd.Timestamp("2026-01-01")]}
        ),
        account_dataset=pd.DataFrame(
            {"account_label": [1], "label_timestamp": [pd.Timestamp("2026-01-01")]}
        ),
    )


def test_valid_case_labels_pass_validation() -> None:
    validate_case_labels(_case_labels())


def test_valid_account_labels_pass_validation() -> None:
    validate_account_labels(_account_labels())


def test_invalid_labels_outside_binary_fail_validation() -> None:
    labels = _case_labels()
    labels.loc[0, "case_label"] = 2
    with pytest.raises(LabelValidationError):
        validate_case_labels(labels)


def test_duplicate_case_labels_fail_validation() -> None:
    labels = pd.concat([_case_labels(), _case_labels()], ignore_index=True)
    with pytest.raises(LabelValidationError):
        validate_case_labels(labels)


def test_duplicate_account_labels_fail_validation() -> None:
    labels = pd.concat([_account_labels(), _account_labels()], ignore_index=True)
    with pytest.raises(LabelValidationError):
        validate_account_labels(labels)


def test_missing_label_timestamps_fail_validation() -> None:
    labels = _case_labels()
    labels.loc[0, "label_timestamp"] = None
    with pytest.raises(LabelValidationError):
        validate_case_labels(labels)


def test_label_quality_summary_includes_class_balance() -> None:
    summary = build_label_quality_summary(_result())
    assert summary["case_labels"]["class_balance"]["positive"] == 1


def test_quality_thresholds_are_enforced() -> None:
    result = LabelDatasetBuildResult(
        case_labels=_case_labels().iloc[0:0],
        account_labels=_account_labels().iloc[0:0],
        case_dataset=pd.DataFrame(),
        account_dataset=pd.DataFrame(),
    )
    with pytest.raises(LabelValidationError):
        validate_label_dataset_result(result)


def test_summary_payloads_are_json_serialisable() -> None:
    json.dumps(build_label_quality_summary(_result()), default=str)


def test_row_count_comparison_reports_warnings_when_counts_differ() -> None:
    result = compare_label_row_counts(pd.DataFrame({"x": [1]}), pd.DataFrame())
    assert result["status"] == "warning"
