"""Filter preparation helpers for dashboard readers and pages."""

from __future__ import annotations

import re

import pandas as pd

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError


def normalise_filter_values(values: object) -> tuple[str, ...]:
    """Normalise scalar and sequence filter values into trimmed strings."""

    try:
        if values is None:
            return ()
        if isinstance(values, str):
            return (values.strip(),) if values.strip() else ()
        if isinstance(values, list | tuple | set):
            clean = [str(value).strip() for value in values if str(value).strip()]
            return tuple(dict.fromkeys(clean))
        return (str(values).strip(),) if str(values).strip() else ()
    except Exception as exc:
        raise DashboardDataError(f"Failed to normalise filter values: {exc}") from exc


def apply_dataframe_search_filter(
    frame: pd.DataFrame,
    search_text: str | None,
    columns: tuple[str, ...] | list[str],
) -> pd.DataFrame:
    """Apply a case-insensitive contains filter without mutating the input frame."""

    try:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a DataFrame")
        query = (search_text or "").strip()
        if not query or frame.empty:
            return frame.copy()
        available = [column for column in columns if column in frame.columns]
        if not available:
            return frame.copy()
        pattern = re.escape(query)
        mask = pd.Series(False, index=frame.index)
        for column in available:
            mask = mask | frame[column].astype(str).str.contains(pattern, case=False, na=False)
        return frame.loc[mask].copy()
    except Exception as exc:
        raise DashboardDataError(f"Failed to apply search filter: {exc}") from exc


def get_default_case_status_filter(config: DashboardConfig | None = None) -> tuple[str, ...]:
    return (config or DashboardConfig()).default_case_statuses


def get_default_risk_band_filter(config: DashboardConfig | None = None) -> tuple[str, ...]:
    return (config or DashboardConfig()).default_risk_bands


def get_default_alert_severity_filter(config: DashboardConfig | None = None) -> tuple[str, ...]:
    return (config or DashboardConfig()).default_alert_severities
