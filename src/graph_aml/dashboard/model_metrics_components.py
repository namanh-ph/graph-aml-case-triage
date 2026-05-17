"""Streamlit renderers for model metric dashboard sections."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import plotly.express as px

from graph_aml.dashboard.components import render_dataframe_table
from graph_aml.dashboard.exceptions import DashboardRenderError


def render_score_distribution_chart(
    scores: pd.DataFrame,
    score_column: str,
    title: str,
) -> None:
    try:
        import streamlit as st

        if not isinstance(scores, pd.DataFrame):
            raise DashboardRenderError("scores must be a DataFrame")
        st.subheader(title)
        if scores.empty or score_column not in scores.columns:
            st.info("No score rows available.")
            return
        fig = px.histogram(scores, x=score_column, nbins=20, title=title)
        st.plotly_chart(fig, use_container_width=True)
    except DashboardRenderError:
        raise
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render score distribution: {exc}") from exc


def render_risk_band_bar_chart(summary: dict[str, object], title: str) -> None:
    try:
        import streamlit as st

        counts = summary.get("risk_band_counts", {}) if isinstance(summary, dict) else {}
        st.subheader(title)
        if not isinstance(counts, Mapping) or not counts:
            st.info("No risk band distribution available.")
            return
        frame = pd.DataFrame(
            [{"risk_band": key, "count": value} for key, value in counts.items()]
        )
        st.plotly_chart(
            px.bar(frame, x="risk_band", y="count", title=title),
            use_container_width=True,
        )
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render risk band chart: {exc}") from exc


def render_model_run_table(model_runs: pd.DataFrame) -> None:
    render_dataframe_table(model_runs, "Model Runs")


def render_precision_at_k_table(precision_at_k: pd.DataFrame) -> None:
    render_dataframe_table(precision_at_k, "Precision At K")


def render_top_ranked_score_table(scores: pd.DataFrame, title: str) -> None:
    render_dataframe_table(scores, title)


def render_model_metrics_summary(summary: dict[str, object]) -> None:
    try:
        import streamlit as st

        st.subheader("Model Metrics Summary")
        st.json(summary)
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render model metrics summary: {exc}") from exc
