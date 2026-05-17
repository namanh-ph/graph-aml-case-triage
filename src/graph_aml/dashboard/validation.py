"""Validation helpers for dashboard data bundles."""

from __future__ import annotations

import json

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], label: str) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise DashboardDataError(f"{label} must be a DataFrame")
    missing = [column for column in columns if column not in frame.columns]
    if missing and not frame.empty:
        raise DashboardDataError(f"{label} is missing required columns: {missing}")


def validate_dashboard_alert_queue(frame: pd.DataFrame) -> None:
    _require_columns(frame, ("alert_id", "severity"), "alert queue")


def validate_dashboard_case_queue(frame: pd.DataFrame) -> None:
    _require_columns(frame, ("case_id", "status"), "case queue")


def validate_dashboard_case_detail(detail: dict[str, pd.DataFrame]) -> None:
    if not isinstance(detail, dict):
        raise DashboardDataError("case detail must be a dictionary")
    for key in (
        "case",
        "case_risk_scores",
        "case_alerts",
        "alerts",
        "case_entities",
        "lifecycle_events",
    ):
        if key not in detail:
            raise DashboardDataError(f"case detail is missing {key}")
        if not isinstance(detail[key], pd.DataFrame):
            raise DashboardDataError(f"case detail {key} must be a DataFrame")


def build_dashboard_data_quality_summary(
    overview_counts: dict[str, object],
    case_queue: pd.DataFrame | None = None,
    alert_queue: pd.DataFrame | None = None,
) -> dict[str, object]:
    def as_int(value: object) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return 0

    summary: dict[str, object] = {
        "transaction_count": as_int(overview_counts.get("transaction_count")),
        "account_count": as_int(overview_counts.get("account_count")),
        "alert_count": as_int(overview_counts.get("alert_count")),
        "case_count": as_int(overview_counts.get("case_count")),
        "case_queue_rows": 0 if case_queue is None else int(len(case_queue)),
        "alert_queue_rows": 0 if alert_queue is None else int(len(alert_queue)),
    }
    try:
        json.dumps(summary, sort_keys=True)
    except TypeError as exc:
        raise DashboardDataError(f"dashboard quality summary is not serialisable: {exc}") from exc
    return summary
