"""Metric aggregation helpers for dashboard pages."""

from __future__ import annotations

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError


def _count(frame: pd.DataFrame | None) -> int:
    return 0 if frame is None else int(len(frame))


def _lower_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame:
        return {}
    return {
        str(key): int(value)
        for key, value in frame[column]
        .dropna()
        .astype(str)
        .str.lower()
        .value_counts()
        .sort_index()
        .items()
    }


def _as_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def build_overview_metric_cards(overview_counts: dict[str, object]) -> list[dict[str, object]]:
    try:
        return [
            {"label": "Transactions", "value": _as_int(overview_counts.get("transaction_count"))},
            {"label": "Accounts", "value": _as_int(overview_counts.get("account_count"))},
            {"label": "Alerts", "value": _as_int(overview_counts.get("alert_count"))},
            {"label": "Cases", "value": _as_int(overview_counts.get("case_count"))},
            {
                "label": "Lifecycle Events",
                "value": _as_int(overview_counts.get("lifecycle_event_count")),
            },
        ]
    except Exception as exc:
        raise DashboardDataError(f"Failed to build overview metric cards: {exc}") from exc


def build_case_queue_metrics(cases: pd.DataFrame) -> dict[str, object]:
    try:
        if not isinstance(cases, pd.DataFrame):
            raise TypeError("cases must be a DataFrame")
        risk_counts = _lower_counts(cases, "risk_band")
        status_counts = _lower_counts(cases, "status")
        return {
            "case_count": _count(cases),
            "open_case_count": int(
                sum(
                    value
                    for key, value in status_counts.items()
                    if not key.startswith("closed") and key != "archived"
                )
            ),
            "critical_case_count": int(risk_counts.get("critical", 0)),
            "high_risk_case_count": int(
                risk_counts.get("high", 0) + risk_counts.get("critical", 0)
            ),
            "risk_band_counts": risk_counts,
            "status_counts": status_counts,
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to build case queue metrics: {exc}") from exc


def build_alert_queue_metrics(alerts: pd.DataFrame) -> dict[str, object]:
    try:
        if not isinstance(alerts, pd.DataFrame):
            raise TypeError("alerts must be a DataFrame")
        severity_counts = _lower_counts(alerts, "severity")
        typology_counts = _lower_counts(alerts, "typology")
        return {
            "alert_count": _count(alerts),
            "critical_alert_count": int(severity_counts.get("critical", 0)),
            "high_alert_count": int(
                severity_counts.get("high", 0) + severity_counts.get("critical", 0)
            ),
            "severity_counts": severity_counts,
            "typology_counts": typology_counts,
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to build alert queue metrics: {exc}") from exc


def build_case_detail_metrics(detail: dict[str, pd.DataFrame]) -> dict[str, object]:
    try:
        if not isinstance(detail, dict):
            raise TypeError("detail must be a dictionary")
        return {
            "case_rows": _count(detail.get("case")),
            "linked_alert_count": _count(detail.get("alerts")),
            "linked_entity_count": _count(detail.get("case_entities")),
            "lifecycle_event_count": _count(detail.get("lifecycle_events")),
            "case_risk_score_rows": _count(detail.get("case_risk_scores")),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to build case detail metrics: {exc}") from exc
