"""Validation helpers for case generation outputs."""

from __future__ import annotations

import json
from typing import Any, cast

import pandas as pd

from graph_aml.cases.exceptions import CaseValidationError
from graph_aml.cases.grouping import (
    CASE_ALERT_LINK_COLUMNS,
    CASE_ENTITY_LINK_COLUMNS,
    CASE_GROUP_COLUMNS,
    CASE_RECORD_COLUMNS,
)


def _missing_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column not in frame.columns]


def _counts(series: pd.Series) -> dict[str, int]:
    if series.empty:
        return {}
    return {
        str(key): int(value)
        for key, value in series.astype(str).value_counts().sort_index().items()
    }


def validate_case_group_frame(groups: pd.DataFrame) -> None:
    missing = _missing_columns(groups, CASE_GROUP_COLUMNS)
    if missing:
        raise CaseValidationError(f"case groups missing columns: {missing}")
    if not groups.empty and groups["case_group_id"].isna().any():
        raise CaseValidationError("case_group_id cannot be null")


def validate_case_generation_result(result: object) -> None:
    payload = cast(Any, result)
    cases = payload.cases
    case_alerts = payload.case_alerts
    missing = _missing_columns(cases, CASE_RECORD_COLUMNS)
    if missing:
        raise CaseValidationError(f"cases missing columns: {missing}")
    if not cases.empty:
        if cases["case_id"].isna().any():
            raise CaseValidationError("case_id cannot be null")
        if cases["case_id"].duplicated().any():
            raise CaseValidationError("case_id must be unique")
        if cases["status"].astype(str).str.strip().eq("").any():
            raise CaseValidationError("status must be non-empty")
        if cases["severity"].astype(str).str.strip().eq("").any():
            raise CaseValidationError("severity must be non-empty")
        priority = pd.to_numeric(cases["priority_score"], errors="coerce")
        if priority.isna().any() or ((priority < 0) | (priority > 100)).any():
            raise CaseValidationError("priority_score must be in [0, 100]")
    alert_missing = _missing_columns(case_alerts, CASE_ALERT_LINK_COLUMNS)
    if alert_missing:
        raise CaseValidationError(f"case_alerts missing columns: {alert_missing}")
    if not case_alerts.empty:
        if case_alerts[list(CASE_ALERT_LINK_COLUMNS)].isna().any().any():
            raise CaseValidationError("case alert links cannot contain null IDs")
        if case_alerts.duplicated(list(CASE_ALERT_LINK_COLUMNS)).any():
            raise CaseValidationError("case alert links must be unique")


def validate_prepared_case_frames(prepared: dict[str, pd.DataFrame]) -> None:
    required = {"cases", "case_alerts", "case_entities"}
    if required.difference(prepared):
        raise CaseValidationError(
            "prepared case frames must include cases, case_alerts, case_entities"
        )
    cases = prepared["cases"]
    if "metadata" not in cases.columns:
        raise CaseValidationError("prepared cases must include metadata")
    validate_case_generation_result(
        type(
            "PreparedCaseResult",
            (),
            {
                "cases": cases,
                "case_alerts": prepared["case_alerts"],
                "case_entities": prepared["case_entities"],
            },
        )()
    )
    entity_missing = _missing_columns(prepared["case_entities"], CASE_ENTITY_LINK_COLUMNS)
    if entity_missing:
        raise CaseValidationError(f"case_entities missing columns: {entity_missing}")


def build_case_generation_quality_summary(result: object) -> dict[str, object]:
    payload = cast(Any, result)
    cases = payload.cases
    case_alerts = payload.case_alerts
    if cases.empty:
        return {
            "case_count": 0,
            "unique_primary_account_count": 0,
            "status_counts": {},
            "severity_counts": {},
            "grouping_strategy_counts": {},
            "duplicate_case_ids": 0,
            "duplicate_alert_links": 0,
            "mean_alert_count": 0.0,
            "max_alert_count": 0,
        }
    alert_count = pd.to_numeric(
        cases.get("alert_count", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)
    return {
        "case_count": int(len(cases)),
        "unique_primary_account_count": int(cases["primary_account_id"].nunique(dropna=True)),
        "status_counts": _counts(cases["status"]),
        "severity_counts": _counts(cases["severity"]),
        "grouping_strategy_counts": _counts(cases["grouping_strategy"]),
        "duplicate_case_ids": int(cases["case_id"].duplicated().sum()),
        "duplicate_alert_links": int(case_alerts.duplicated(list(CASE_ALERT_LINK_COLUMNS)).sum())
        if not case_alerts.empty
        else 0,
        "mean_alert_count": float(alert_count.mean()) if len(alert_count) else 0.0,
        "max_alert_count": int(alert_count.max()) if len(alert_count) else 0,
    }


def compare_case_row_counts(
    source_cases: pd.DataFrame, persisted_cases: pd.DataFrame
) -> dict[str, object]:
    source_count = int(len(source_cases))
    persisted_count = int(len(persisted_cases))
    warnings: list[str] = []
    if source_count != persisted_count:
        warnings.append("source and persisted case row counts differ")
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }


def assert_json_serialisable(payload: dict[str, object]) -> None:
    try:
        json.dumps(payload, sort_keys=True, default=str)
    except TypeError as exc:
        raise CaseValidationError(f"payload is not JSON serialisable: {exc}") from exc
