"""Summary helpers for analyst labels."""

from __future__ import annotations

import pandas as pd

from graph_aml.labels.dataset import LabelDatasetBuildResult


def _label_summary(frame: pd.DataFrame, label_column: str) -> dict[str, object]:
    if frame.empty or label_column not in frame.columns:
        return {
            "row_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "class_balance": {},
            "label_timestamp_min": None,
            "label_timestamp_max": None,
        }
    positives = int((frame[label_column] == 1).sum())
    negatives = int((frame[label_column] == 0).sum())
    timestamps = pd.to_datetime(frame.get("label_timestamp"), errors="coerce")
    return {
        "row_count": int(len(frame)),
        "positive_count": positives,
        "negative_count": negatives,
        "class_balance": {"positive": positives, "negative": negatives},
        "label_timestamp_min": str(timestamps.min()) if timestamps.notna().any() else None,
        "label_timestamp_max": str(timestamps.max()) if timestamps.notna().any() else None,
    }


def summarise_case_labels(case_labels: pd.DataFrame) -> dict[str, object]:
    return _label_summary(case_labels, "case_label")


def summarise_account_labels(account_labels: pd.DataFrame) -> dict[str, object]:
    return _label_summary(account_labels, "account_label")


def summarise_supervised_dataset(frame: pd.DataFrame, label_column: str) -> dict[str, object]:
    summary = _label_summary(frame, label_column)
    summary["missing_feature_counts"] = {
        str(column): int(frame[column].isna().sum())
        for column in frame.columns
        if column not in {label_column, "label_name", "label_timestamp"}
    }
    return summary


def label_dataset_result_to_dict(result: LabelDatasetBuildResult) -> dict[str, object]:
    return {
        "case_labels": summarise_case_labels(result.case_labels),
        "account_labels": summarise_account_labels(result.account_labels),
        "case_dataset": summarise_supervised_dataset(result.case_dataset, "case_label"),
        "account_dataset": summarise_supervised_dataset(result.account_dataset, "account_label"),
        "summary": result.summary,
        "metadata": result.metadata,
    }
