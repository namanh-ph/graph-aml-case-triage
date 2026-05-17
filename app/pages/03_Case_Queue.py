"""Case queue page for generated AML cases."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardDataError,
    apply_dataframe_search_filter,
    build_case_queue_metrics,
    create_dashboard_engine,
    dispose_dashboard_engine,
    get_default_case_status_filter,
    get_default_risk_band_filter,
    load_dashboard_config,
    read_dashboard_case_queue,
    read_dashboard_filter_options,
)
from graph_aml.dashboard.components import render_dataframe_table, render_metric_cards  # noqa: E402


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Case Queue",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Case Queue")

    engine = None
    try:
        engine = create_dashboard_engine()
        options = read_dashboard_filter_options(engine)
        statuses = st.multiselect(
            "Case status",
            options.get("case_statuses", []),
            default=[
                value
                for value in get_default_case_status_filter(config)
                if value in options.get("case_statuses", [])
            ],
        )
        risk_bands = st.multiselect(
            "Risk band",
            options.get("case_risk_bands", []),
            default=[
                value
                for value in get_default_risk_band_filter(config)
                if value in options.get("case_risk_bands", [])
            ],
        )
        assigned_to = st.selectbox("Assigned analyst", [""] + options.get("assigned_to", []))
        search = st.text_input("Account ID or case ID search")
        row_limit = st.number_input(
            "Row limit",
            min_value=1,
            max_value=config.max_page_size,
            value=config.default_page_size,
            step=10,
        )
        cases = read_dashboard_case_queue(
            engine,
            statuses=statuses,
            risk_bands=risk_bands,
            assigned_to=assigned_to or None,
            limit=int(row_limit),
        )
        cases = apply_dataframe_search_filter(
            cases,
            search,
            ["case_id", "primary_account_id", "primary_customer_id"],
        )
        metrics = build_case_queue_metrics(cases)
        render_metric_cards(
            [
                {"label": "Cases", "value": metrics["case_count"]},
                {"label": "Open", "value": metrics["open_case_count"]},
                {"label": "High/Critical", "value": metrics["high_risk_case_count"]},
                {"label": "Critical", "value": metrics["critical_case_count"]},
            ]
        )
        display_columns = [
            column
            for column in (
                "case_id",
                "status",
                "severity",
                "priority_score",
                "case_risk_score",
                "risk_band",
                "risk_rank",
                "primary_account_id",
                "primary_customer_id",
                "alert_count",
                "typologies",
                "assigned_to",
                "queue",
                "updated_at",
            )
            if column in cases.columns
        ]
        render_dataframe_table(
            cases[display_columns] if display_columns else cases,
            "Cases",
            height=520,
        )
        if config.enable_download_buttons and not cases.empty:
            st.download_button(
                "Download CSV",
                cases.to_csv(index=False),
                file_name="dashboard_case_queue.csv",
                mime="text/csv",
            )
        st.info(
            "Copy a case ID into the Case Detail page to review evidence and lifecycle history."
        )
    except DashboardDataError as exc:
        st.info(f"No case queue data is available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
