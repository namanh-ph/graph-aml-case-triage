"""Audit Log page for governance event review."""

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
    build_audit_event_summary,
    create_dashboard_engine,
    dataframe_to_csv_bytes,
    dataframe_to_json_bytes,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_dashboard_audit_events,
    read_dashboard_audit_filter_options,
    render_audit_event_detail,
    render_audit_event_table,
    render_audit_summary,
    safe_download_filename,
)


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Audit Log",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Audit Log")
    engine = None
    try:
        engine = create_dashboard_engine()
        options = read_dashboard_audit_filter_options(engine)
        with st.sidebar:
            components = st.multiselect(
                "Component",
                options.get("components", []),
                default=[
                    value
                    for value in config.audit_log.default_components
                    if value in options.get("components", [])
                ],
            )
            event_types = st.multiselect("Event type", options.get("event_types", []))
            statuses = st.multiselect("Status", options.get("statuses", []))
            run_id = st.text_input("Run ID")
            search_text = st.text_input("Search text")
            limit = st.number_input(
                "Row limit",
                min_value=1,
                max_value=config.audit_log.max_limit,
                value=config.audit_log.default_limit,
            )
        events = read_dashboard_audit_events(
            engine,
            components=components or None,
            event_types=event_types or None,
            statuses=statuses or None,
            run_id=run_id or None,
            search_text=search_text or None,
            limit=int(limit),
        )
        render_audit_summary(build_audit_event_summary(events))
        render_audit_event_table(events)
        if not events.empty:
            selected = st.selectbox(
                "Audit event detail",
                events["audit_event_id"].astype(str).tolist(),
            )
            row = events.loc[events["audit_event_id"].astype(str) == selected].iloc[0]
            with st.expander("Selected Event Detail", expanded=False):
                render_audit_event_detail(row)
        if config.enable_download_buttons:
            st.download_button(
                "Download Audit CSV",
                dataframe_to_csv_bytes(events),
                file_name=safe_download_filename("audit_events"),
                mime="text/csv",
            )
            st.download_button(
                "Download Audit JSON",
                dataframe_to_json_bytes(events),
                file_name=safe_download_filename("audit_events", "json"),
                mime="application/json",
            )
    except DashboardDataError as exc:
        st.info(f"Audit events are not available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
