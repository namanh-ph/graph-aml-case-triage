"""Null-safe formatting helpers for dashboard display."""

from __future__ import annotations

import json
from datetime import date, datetime

import pandas as pd


def _is_missing(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def format_score(value: object, decimals: int = 2) -> str:
    if value is None or _is_missing(value):
        return "-"
    try:
        return f"{float(str(value)):.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


def format_amount(value: object, currency: str = "AUD", decimals: int = 2) -> str:
    if value is None or _is_missing(value):
        return "-"
    try:
        return f"{currency} {float(str(value)):,.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


def format_timestamp(value: object, timestamp_format: str = "%Y-%m-%d %H:%M:%S") -> str:
    if value is None or _is_missing(value):
        return "-"
    try:
        timestamp = pd.to_datetime(value)
        if pd.isna(timestamp):
            return "-"
        return str(timestamp.strftime(timestamp_format))
    except Exception:
        return str(value)


def format_risk_band(value: object) -> str:
    if value is None or _is_missing(value):
        return "Unscored"
    return str(value).strip().replace("_", " ").title()


def format_case_status(value: object) -> str:
    if value is None or _is_missing(value):
        return "Unknown"
    return str(value).strip() or "Unknown"


def _compact(value: object) -> object:
    if isinstance(value, dict | list | tuple | set):
        return json.dumps(value, sort_keys=True, default=str)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def dataframe_for_display(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a display-safe copy with compact JSON-like cells."""

    display = frame.copy()
    for column in display.columns:
        display[column] = display[column].map(_compact)
    return display
