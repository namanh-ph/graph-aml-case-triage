"""Overview page for the local AML dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardDataError,
    build_overview_metric_cards,
    create_dashboard_engine,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_dashboard_overview_counts,
)
from graph_aml.dashboard.components import render_dataframe_table, render_metric_cards  # noqa: E402


def _distribution_frame(payload: dict[str, object], key: str) -> pd.DataFrame:
    value = payload.get(key) or {}
    if not isinstance(value, dict):
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {"label": str(item_key), "count": int(item_value)}
            for item_key, item_value in value.items()
        ]
    )


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Overview",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Overview")

    engine = None
    try:
        engine = create_dashboard_engine()
        overview = read_dashboard_overview_counts(engine)
        render_metric_cards(build_overview_metric_cards(overview))
        left, right = st.columns(2)
        with left:
            render_dataframe_table(
                _distribution_frame(overview, "case_status_counts"), "Case Status Counts"
            )
            render_dataframe_table(
                _distribution_frame(overview, "case_risk_band_counts"),
                "Case Risk Band Counts",
            )
        with right:
            render_dataframe_table(
                _distribution_frame(overview, "alert_severity_counts"),
                "Alert Severity Counts",
            )
            render_dataframe_table(
                _distribution_frame(overview, "alert_typology_counts"),
                "Alert Typology Counts",
            )
        st.info("If the dashboard is empty, run the documented backend preparation workflow first.")
    except DashboardDataError as exc:
        st.info(f"No dashboard data is available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
