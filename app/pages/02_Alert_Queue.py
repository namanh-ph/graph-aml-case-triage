"""Alert queue page for persisted AML alerts."""

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
    build_alert_queue_metrics,
    create_dashboard_engine,
    dispose_dashboard_engine,
    get_default_alert_severity_filter,
    load_dashboard_config,
    read_dashboard_alert_queue,
    read_dashboard_filter_options,
)
from graph_aml.dashboard.components import render_dataframe_table, render_metric_cards  # noqa: E402


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Alert Queue",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Alert Queue")

    engine = None
    try:
        engine = create_dashboard_engine()
        options = read_dashboard_filter_options(engine)
        severities = st.multiselect(
            "Severity",
            options.get("alert_severities", []),
            default=[
                value
                for value in get_default_alert_severity_filter(config)
                if value in options.get("alert_severities", [])
            ],
        )
        typologies = st.multiselect("Typology", options.get("alert_typologies", []))
        account_search = st.text_input("Account ID search")
        row_limit = st.number_input(
            "Row limit",
            min_value=1,
            max_value=config.max_page_size,
            value=config.default_page_size,
            step=10,
        )
        alerts = read_dashboard_alert_queue(
            engine,
            severities=severities,
            typologies=typologies,
            account_id=account_search or None,
            limit=int(row_limit),
        )
        metrics = build_alert_queue_metrics(alerts)
        render_metric_cards(
            [
                {"label": "Alerts", "value": metrics["alert_count"]},
                {"label": "High/Critical", "value": metrics["high_alert_count"]},
                {"label": "Critical", "value": metrics["critical_alert_count"]},
            ]
        )
        display_columns = [
            column
            for column in (
                "alert_id",
                "account_id",
                "customer_id",
                "rule_name",
                "typology",
                "severity",
                "risk_score_rule",
                "reason_code",
                "evidence_ids",
                "created_at",
            )
            if column in alerts.columns
        ]
        render_dataframe_table(
            alerts[display_columns] if display_columns else alerts,
            "Alerts",
            height=520,
        )
        if config.enable_download_buttons and not alerts.empty:
            st.download_button(
                "Download CSV",
                alerts.to_csv(index=False),
                file_name="dashboard_alert_queue.csv",
                mime="text/csv",
            )
    except DashboardDataError as exc:
        st.info(f"No alert queue data is available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
