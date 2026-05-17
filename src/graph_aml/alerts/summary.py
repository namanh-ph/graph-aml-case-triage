"""Summary utilities for AML alerts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from graph_aml.alerts.dataframe import alerts_to_dataframe, normalise_alert_dataframe
from graph_aml.alerts.schema import AlertRecord


def summarise_alerts(
    alerts: pd.DataFrame | tuple[AlertRecord, ...] | list[AlertRecord],
) -> dict[str, object]:
    """Return JSON-serialisable alert summary metrics."""

    if isinstance(alerts, pd.DataFrame):
        frame = normalise_alert_dataframe(alerts) if not alerts.empty else alerts.copy()
    else:
        frame = alerts_to_dataframe(alerts)

    summary: dict[str, Any] = {
        "alert_count": 0,
        "unique_account_count": 0,
        "unique_customer_count": 0,
        "severity_counts": {},
        "status_counts": {},
        "rule_name_counts": {},
        "typology_counts": {},
        "min_detection_window_start": None,
        "max_detection_window_end": None,
        "mean_rule_score": 0.0,
        "max_rule_score": 0.0,
        "evidence_id_count": 0,
    }
    if frame.empty:
        return summary

    scores = pd.to_numeric(frame["risk_score_rule"], errors="coerce").fillna(0.0)
    starts = pd.to_datetime(frame["detection_window_start"], utc=True, errors="coerce")
    ends = pd.to_datetime(frame["detection_window_end"], utc=True, errors="coerce")
    summary.update(
        {
            "alert_count": int(len(frame)),
            "unique_account_count": int(frame["account_id"].nunique(dropna=True)),
            "unique_customer_count": int(frame["customer_id"].nunique(dropna=True)),
            "severity_counts": _counts(frame["severity"]),
            "status_counts": _counts(frame["alert_status"]),
            "rule_name_counts": _counts(frame["rule_name"]),
            "typology_counts": _counts(frame["typology"]),
            "min_detection_window_start": _timestamp_string(starts.min()),
            "max_detection_window_end": _timestamp_string(ends.max()),
            "mean_rule_score": float(scores.mean()),
            "max_rule_score": float(scores.max()),
            "evidence_id_count": int(sum(len(value) for value in frame["evidence_ids"])),
        }
    )
    return summary


def _counts(series: pd.Series) -> dict[str, int]:
    values = series.dropna().astype(str).sort_values(kind="mergesort")
    return {str(key): int(value) for key, value in values.value_counts(sort=False).items()}


def _timestamp_string(value: object) -> str | None:
    if pd.isna(value):
        return None
    return str(pd.Timestamp(value).isoformat())
