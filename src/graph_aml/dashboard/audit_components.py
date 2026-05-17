"""Audit dashboard summary and render helpers."""

from __future__ import annotations

import json

import pandas as pd

from graph_aml.dashboard.components import render_dataframe_table
from graph_aml.dashboard.exceptions import DashboardRenderError


def build_audit_event_summary(events: pd.DataFrame) -> dict[str, object]:
    if not isinstance(events, pd.DataFrame):
        raise DashboardRenderError("events must be a DataFrame")
    status = events.get("status", pd.Series(dtype=str)).dropna().astype(str)
    return {
        "event_count": int(len(events)),
        "component_counts": events.get("component", pd.Series(dtype=str)).value_counts().to_dict(),
        "event_type_counts": events.get(
            "event_type",
            pd.Series(dtype=str),
        ).value_counts().to_dict(),
        "status_counts": status.value_counts().to_dict(),
        "failure_count": int(status.str.lower().isin({"failed", "failure", "error"}).sum()),
        "latest_event_timestamp": None
        if events.empty or "event_timestamp" not in events
        else str(events["event_timestamp"].max()),
    }


def flatten_audit_details_for_display(events: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(events, pd.DataFrame):
        raise DashboardRenderError("events must be a DataFrame")
    frame = events.copy(deep=True)
    if "details" in frame.columns:
        frame["details"] = frame["details"].map(
            lambda value: json.dumps(value, sort_keys=True, default=str)
            if isinstance(value, dict | list)
            else value
        )
    return frame


def render_audit_summary(summary: dict[str, object]) -> None:
    try:
        import streamlit as st

        st.subheader("Audit Summary")
        st.json(summary)
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render audit summary: {exc}") from exc


def render_audit_event_table(events: pd.DataFrame) -> None:
    render_dataframe_table(flatten_audit_details_for_display(events), "Audit Events")


def render_audit_event_detail(event_row: pd.Series | dict[str, object]) -> None:
    try:
        import streamlit as st

        row = event_row.to_dict() if isinstance(event_row, pd.Series) else dict(event_row)
        if not row:
            st.info("No audit event selected.")
            return
        st.json(row)
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render audit event detail: {exc}") from exc
