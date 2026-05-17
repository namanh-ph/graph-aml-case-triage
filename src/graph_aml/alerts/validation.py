"""Validation utilities for AML alert records and DataFrames."""

from __future__ import annotations

import pandas as pd

from graph_aml.alerts.exceptions import AlertValidationError
from graph_aml.alerts.schema import (
    ALERT_COLUMNS,
    AlertRecord,
    alert_record_from_dict,
    alert_record_to_dict,
)


def validate_alert_record(alert: AlertRecord) -> None:
    """Validate a single alert record."""

    alert_record_from_dict(alert_record_to_dict(alert))


def validate_alert_records(alerts: tuple[AlertRecord, ...] | list[AlertRecord]) -> None:
    """Validate a collection of alert records."""

    for alert in alerts:
        validate_alert_record(alert)


def validate_alert_dataframe(frame: pd.DataFrame) -> None:
    """Validate alert DataFrame shape and row-level constraints."""

    missing = set(ALERT_COLUMNS).difference(frame.columns)
    if missing:
        raise AlertValidationError(f"alert DataFrame is missing columns: {sorted(missing)}")
    if frame.empty:
        return
    if frame["alert_id"].duplicated().any():
        raise AlertValidationError("alert_id values must be unique")
    for record in frame.loc[:, ALERT_COLUMNS].astype(object).to_dict(orient="records"):
        alert_record_from_dict(record)
