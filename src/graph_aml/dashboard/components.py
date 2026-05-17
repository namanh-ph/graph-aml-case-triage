"""Reusable Streamlit components for the AML dashboard."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardRenderError
from graph_aml.dashboard.formatting import dataframe_for_display


def _st() -> Any:
    import streamlit as st

    return st


def render_metric_cards(metrics: list[dict[str, object]]) -> None:
    try:
        st = _st()
        columns = st.columns(max(1, min(len(metrics), 5)))
        for index, metric in enumerate(metrics):
            with columns[index % len(columns)]:
                st.metric(str(metric.get("label", "Metric")), metric.get("value", 0))
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render metric cards: {exc}") from exc


def render_dataframe_table(
    frame: pd.DataFrame,
    title: str | None = None,
    height: int | None = None,
) -> None:
    try:
        st = _st()
        if title:
            st.subheader(title)
        if frame.empty:
            st.info("No rows available.")
        else:
            if height is None:
                st.dataframe(dataframe_for_display(frame), use_container_width=True)
            else:
                st.dataframe(
                    dataframe_for_display(frame), use_container_width=True, height=height
                )
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render table: {exc}") from exc


def render_alert_summary(alerts: pd.DataFrame) -> None:
    render_dataframe_table(alerts, "Linked Alerts")


def render_case_summary(case_row: pd.Series | dict[str, object]) -> None:
    try:
        st = _st()
        row = case_row.to_dict() if isinstance(case_row, pd.Series) else dict(case_row)
        if not row:
            st.info("No case record available.")
            return
        st.subheader(f"Case {row.get('case_id', '')}")
        st.write(
            {
                "status": row.get("status"),
                "severity": row.get("severity"),
                "priority_score": row.get("priority_score"),
                "primary_account_id": row.get("primary_account_id"),
                "assigned_to": row.get("assigned_to"),
                "queue": row.get("queue"),
            }
        )
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render case summary: {exc}") from exc


def render_case_risk_summary(case_risk_scores: pd.DataFrame) -> None:
    render_dataframe_table(case_risk_scores.head(5), "Case Risk Scores")


def _render_json_section(title: str, payload: object) -> None:
    st = _st()
    st.markdown(f"**{title}**")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            st.write(payload)
            return
    st.json(payload)


def render_case_evidence_pack(evidence_pack: pd.DataFrame) -> None:
    try:
        st = _st()
        st.subheader("Evidence Pack")
        if evidence_pack.empty:
            st.info("No evidence pack has been persisted for this case.")
            return
        row = evidence_pack.iloc[0].to_dict()
        for column in (
            "case_summary",
            "typology_evidence",
            "alert_evidence",
            "transaction_evidence",
            "account_evidence",
            "graph_evidence",
            "risk_driver_evidence",
            "chronology",
            "recommended_review_focus",
            "evidence_quality",
        ):
            if column in row:
                _render_json_section(column.replace("_", " ").title(), row[column])
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render evidence pack: {exc}") from exc


def render_case_explanation(explanations: pd.DataFrame) -> None:
    try:
        st = _st()
        st.subheader("Deterministic Explanation")
        if explanations.empty:
            st.info("No explanation has been persisted for this case.")
            return
        row = explanations.iloc[0].to_dict()
        st.write(row.get("explanation_text", ""))
        bullets = row.get("explanation_bullets") or []
        if isinstance(bullets, str):
            try:
                bullets = json.loads(bullets)
            except json.JSONDecodeError:
                bullets = [bullets]
        for bullet in bullets:
            st.markdown(f"- {bullet}")
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render explanation: {exc}") from exc


def render_lifecycle_events(events: pd.DataFrame) -> None:
    render_dataframe_table(events, "Lifecycle Events")


def render_empty_state(message: str) -> None:
    st = _st()
    st.info(message)


def render_error_message(message: str) -> None:
    st = _st()
    st.error(message)
