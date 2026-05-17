"""Validation helpers for AML case lifecycle records."""

from __future__ import annotations

import pandas as pd

from graph_aml.cases.exceptions import CaseLifecycleValidationError

LIFECYCLE_EVENT_REQUIRED_COLUMNS = (
    "action_id",
    "case_id",
    "action_type",
    "analyst_id",
    "action_timestamp",
)
CASE_ASSIGNMENT_REQUIRED_COLUMNS = ("case_id", "assigned_to", "queue")


def _missing_columns(frame: pd.DataFrame, required: tuple[str, ...]) -> list[str]:
    return [column for column in required if column not in frame.columns]


def validate_lifecycle_event_frame(events: pd.DataFrame) -> None:
    missing = _missing_columns(events, LIFECYCLE_EVENT_REQUIRED_COLUMNS)
    if missing:
        raise CaseLifecycleValidationError(f"missing lifecycle event columns: {missing}")
    if events.empty:
        return
    for column in ("action_id", "case_id", "action_type", "analyst_id"):
        if events[column].isna().any() or (events[column].astype(str).str.strip() == "").any():
            raise CaseLifecycleValidationError(f"{column} values must be non-empty")
    if events["action_timestamp"].isna().any():
        raise CaseLifecycleValidationError("action_timestamp values must be non-empty")
    if events["action_id"].duplicated().any():
        raise CaseLifecycleValidationError("duplicate action IDs are not allowed")


def validate_case_assignment_frame(assignments: pd.DataFrame) -> None:
    missing = _missing_columns(assignments, CASE_ASSIGNMENT_REQUIRED_COLUMNS)
    if missing:
        raise CaseLifecycleValidationError(f"missing case assignment columns: {missing}")
    if assignments.empty:
        return
    if (
        assignments["case_id"].isna().any()
        or (assignments["case_id"].astype(str).str.strip() == "").any()
    ):
        raise CaseLifecycleValidationError("case_id values must be non-empty")


def build_case_lifecycle_quality_summary(events: pd.DataFrame) -> dict[str, object]:
    try:
        duplicate_action_ids = (
            int(events["action_id"].duplicated().sum()) if "action_id" in events else 0
        )
        missing_case_ids = (
            int(events["case_id"].isna().sum())
            + int((events["case_id"].astype(str).str.strip() == "").sum())
            if "case_id" in events
            else 0
        )
        latest = (
            events["action_timestamp"].max()
            if "action_timestamp" in events and not events.empty
            else None
        )
        return {
            "event_count": int(len(events)),
            "unique_case_count": int(events["case_id"].nunique(dropna=True))
            if "case_id" in events
            else 0,
            "unique_analyst_count": int(events["analyst_id"].nunique(dropna=True))
            if "analyst_id" in events
            else 0,
            "action_type_counts": {
                str(key): int(value)
                for key, value in events.get("action_type", pd.Series(dtype=str))
                .value_counts()
                .sort_index()
                .items()
            },
            "missing_case_ids": int(missing_case_ids),
            "duplicate_action_ids": int(duplicate_action_ids),
            "latest_action_timestamp": None if latest is None or pd.isna(latest) else str(latest),
        }
    except Exception as exc:
        raise CaseLifecycleValidationError(
            f"Failed to build lifecycle quality summary: {exc}"
        ) from exc


def compare_case_lifecycle_event_counts(
    source_count: int,
    persisted_events: pd.DataFrame,
) -> dict[str, object]:
    persisted_count = int(len(persisted_events))
    warnings: list[str] = []
    if int(source_count) != persisted_count:
        warnings.append("row count mismatch")
    return {
        "source_row_count": int(source_count),
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }
