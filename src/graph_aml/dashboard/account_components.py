"""Streamlit account profile components."""

from __future__ import annotations

import pandas as pd

from graph_aml.dashboard.components import render_dataframe_table, render_metric_cards
from graph_aml.dashboard.exceptions import DashboardRenderError


def render_account_header(header: pd.DataFrame) -> None:
    try:
        import streamlit as st

        st.subheader("Account")
        if header.empty:
            st.info("No account record found.")
            return
        row = header.iloc[0].to_dict()
        st.write(
            {
                "account_id": row.get("account_id"),
                "customer_id": row.get("customer_id"),
                "customer_name": row.get("customer_name"),
                "account_status": row.get("account_status"),
                "customer_risk_rating": row.get("customer_risk_rating"),
                "account_risk_band": row.get("account_risk_band"),
                "community_id": row.get("community_id"),
            }
        )
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render account header: {exc}") from exc


def render_account_metric_cards(metrics: dict[str, object]) -> None:
    render_metric_cards(
        [
            {"label": "Transactions", "value": metrics.get("transaction_count", 0)},
            {"label": "Alerts", "value": metrics.get("alert_count", 0)},
            {"label": "Linked Cases", "value": metrics.get("linked_case_count", 0)},
            {"label": "Risk Score", "value": metrics.get("latest_account_risk_score", "-")},
        ]
    )


def render_account_transactions(transactions: pd.DataFrame) -> None:
    render_dataframe_table(transactions, "Transactions", height=360)


def render_account_alerts(alerts: pd.DataFrame) -> None:
    render_dataframe_table(alerts, "Alerts", height=320)


def render_account_cases(cases: pd.DataFrame) -> None:
    render_dataframe_table(cases, "Linked Cases", height=320)


def render_account_features(features: dict[str, pd.DataFrame]) -> None:
    try:
        import streamlit as st

        st.subheader("Features")
        for name, frame in features.items():
            with st.expander(name.replace("_", " ").title(), expanded=False):
                render_dataframe_table(frame)
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render account features: {exc}") from exc


def render_account_counterparties(counterparties: pd.DataFrame) -> None:
    render_dataframe_table(counterparties, "Counterparties", height=320)
