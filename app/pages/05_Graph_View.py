"""Graph View page for suspicious account and counterparty context."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardDataError,
    DashboardRenderError,
    build_graph_view_frames,
    create_dashboard_engine,
    dataframe_to_csv_bytes,
    dataframe_to_json_bytes,
    dict_to_json_bytes,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_graph_view_context,
    render_graph_legend,
    render_graph_summary,
    render_graph_view,
    safe_download_filename,
    summarise_graph_view,
)
from graph_aml.dashboard.components import render_dataframe_table  # noqa: E402


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Graph View",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Graph View")
    st.caption("PostgreSQL-backed account, counterparty, transaction, alert, and case context.")

    with st.sidebar:
        st.subheader("Seed")
        case_id = st.text_input("Case ID")
        account_id = st.text_input("Account ID")
        community_id = st.text_input("Community ID")
        risk_band = st.selectbox("Risk band", ["", "low", "medium", "high", "critical"])
        max_hops = st.number_input(
            "Max hops",
            min_value=1,
            max_value=config.graph_view.max_hops,
            value=config.graph_view.max_hops,
        )
        max_nodes = st.number_input(
            "Max nodes",
            min_value=1,
            max_value=config.graph_view.max_nodes,
            value=config.graph_view.max_nodes,
        )
        max_edges = st.number_input(
            "Max edges",
            min_value=1,
            max_value=config.graph_view.max_edges,
            value=config.graph_view.max_edges,
        )

    graph_config = replace(
        config,
        graph_view=replace(
            config.graph_view,
            max_hops=int(max_hops),
            max_nodes=int(max_nodes),
            max_edges=int(max_edges),
        ),
    )

    engine = None
    try:
        engine = create_dashboard_engine()
        context = read_graph_view_context(
            engine,
            case_id=case_id or None,
            account_id=account_id or None,
            community_id=community_id or None,
            risk_band=risk_band or None,
            config=graph_config,
        )
        frames = build_graph_view_frames(context, graph_config)
        summary = summarise_graph_view(frames["nodes"], frames["edges"])
        render_graph_summary(summary)
        if config.graph_view.show_legend:
            render_graph_legend()
        render_graph_view(frames["nodes"], frames["edges"], graph_config)

        with st.expander("Nodes", expanded=False):
            render_dataframe_table(frames["nodes"])
        with st.expander("Edges", expanded=False):
            render_dataframe_table(frames["edges"])

        if config.enable_download_buttons:
            left, middle, right = st.columns(3)
            with left:
                st.download_button(
                    "Download Nodes CSV",
                    dataframe_to_csv_bytes(frames["nodes"]),
                    file_name=safe_download_filename("graph_nodes"),
                    mime="text/csv",
                )
            with middle:
                st.download_button(
                    "Download Edges CSV",
                    dataframe_to_csv_bytes(frames["edges"]),
                    file_name=safe_download_filename("graph_edges"),
                    mime="text/csv",
                )
            with right:
                st.download_button(
                    "Download Graph JSON",
                    dict_to_json_bytes(
                        {
                            "summary": summary,
                            "nodes": dataframe_to_json_bytes(frames["nodes"]).decode("utf-8"),
                            "edges": dataframe_to_json_bytes(frames["edges"]).decode("utf-8"),
                        }
                    ),
                    file_name=safe_download_filename("graph_context", "json"),
                    mime="application/json",
                )
    except (DashboardDataError, DashboardRenderError) as exc:
        st.info(f"No graph context is available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
