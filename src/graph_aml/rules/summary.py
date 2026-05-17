"""Rule output summary helpers."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from graph_aml.alerts import AlertRecord, summarise_alerts
from graph_aml.rules.circular_flow import CIRCULAR_FLOW_DETECTION_COLUMNS
from graph_aml.rules.common import require_columns


def summarise_rule_alerts(alerts: tuple[AlertRecord, ...] | list[AlertRecord]) -> dict[str, object]:
    """Return JSON-serialisable summary metrics for rule alerts."""

    alert_summary = summarise_alerts(alerts)
    return {
        "alert_count": alert_summary["alert_count"],
        "unique_account_count": alert_summary["unique_account_count"],
        "unique_customer_count": alert_summary["unique_customer_count"],
        "severity_counts": alert_summary["severity_counts"],
        "typology_counts": alert_summary["typology_counts"],
        "rule_name_counts": alert_summary["rule_name_counts"],
        "evidence_transaction_count": alert_summary["evidence_id_count"],
        "min_detection_window_start": alert_summary["min_detection_window_start"],
        "max_detection_window_end": alert_summary["max_detection_window_end"],
        "mean_rule_score": alert_summary["mean_rule_score"],
        "max_rule_score": alert_summary["max_rule_score"],
    }


def summarise_circular_flow_detections(detections: pd.DataFrame) -> dict[str, object]:
    """Return JSON-serialisable summary metrics for circular-flow detections."""

    require_columns(detections, CIRCULAR_FLOW_DETECTION_COLUMNS, "detections")
    if detections.empty:
        return {
            "cycle_count": 0,
            "unique_primary_account_count": 0,
            "unique_account_count": 0,
            "min_cycle_length": None,
            "max_cycle_length": None,
            "mean_cycle_length": None,
            "min_time_span_hours": None,
            "max_time_span_hours": None,
            "mean_time_span_hours": None,
            "total_evidence_transaction_count": 0,
            "mean_total_amount": None,
            "max_total_amount": None,
        }

    cycle_lengths = pd.to_numeric(detections["cycle_length"], errors="coerce")
    time_spans = pd.to_numeric(detections["time_span_hours"], errors="coerce")
    total_amounts = pd.to_numeric(detections["total_amount"], errors="coerce")
    accounts: set[str] = set()
    for value in detections["cycle_accounts"]:
        if isinstance(value, tuple | list):
            accounts.update(str(item) for item in value)
    evidence_count = sum(
        len(cast(Any, value)) if isinstance(value, tuple | list) else 0
        for value in detections["evidence_ids"]
    )
    return {
        "cycle_count": int(len(detections)),
        "unique_primary_account_count": int(detections["primary_account_id"].nunique()),
        "unique_account_count": int(len(accounts)),
        "min_cycle_length": _optional_number(cycle_lengths.min(), as_int=True),
        "max_cycle_length": _optional_number(cycle_lengths.max(), as_int=True),
        "mean_cycle_length": _optional_number(cycle_lengths.mean()),
        "min_time_span_hours": _optional_number(time_spans.min()),
        "max_time_span_hours": _optional_number(time_spans.max()),
        "mean_time_span_hours": _optional_number(time_spans.mean()),
        "total_evidence_transaction_count": int(evidence_count),
        "mean_total_amount": _optional_number(total_amounts.mean()),
        "max_total_amount": _optional_number(total_amounts.max()),
    }


def _optional_number(value: object, *, as_int: bool = False) -> int | float | None:
    if value is None or pd.isna(value):
        return None
    if as_int:
        return int(cast(Any, value))
    return float(cast(Any, value))
