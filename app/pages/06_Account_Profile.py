"""Account Profile page for account-level AML investigation."""

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
    build_account_profile_metrics,
    create_dashboard_engine,
    dataframe_to_csv_bytes,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_account_profile,
    safe_download_filename,
)
from graph_aml.dashboard.account_components import (  # noqa: E402
    render_account_alerts,
    render_account_cases,
    render_account_counterparties,
    render_account_features,
    render_account_header,
    render_account_metric_cards,
    render_account_transactions,
)


def _download_frame(label: str, frame, filename_prefix: str) -> None:
    if frame.empty:
        return
    st.download_button(
        label,
        dataframe_to_csv_bytes(frame),
        file_name=safe_download_filename(filename_prefix),
        mime="text/csv",
    )


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Account Profile",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Account Profile")
    account_id = st.text_input("Account ID")
    if not account_id.strip():
        st.info("Enter an account ID to inspect customer context, risk, alerts, and linked cases.")
        return

    engine = None
    try:
        engine = create_dashboard_engine()
        profile = read_account_profile(engine, account_id.strip(), config)
        render_account_header(profile["header"])
        if profile["header"].empty:
            st.info("No account was found for the supplied ID.")
            return
        metrics = build_account_profile_metrics(profile)
        render_account_metric_cards(metrics)
        render_account_transactions(profile["transactions"])
        render_account_alerts(profile["alerts"])
        if config.account_profile.show_linked_cases:
            render_account_cases(profile["cases"])
        render_account_counterparties(profile["counterparties"])
        feature_frames = {
            "behavioural_features": profile["behavioural_features"],
            "graph_features": profile["graph_features"],
            "anomaly_scores": profile["anomaly_scores"],
            "account_risk_scores": profile["account_risk_scores"],
        }
        visible_features = {
            name: frame
            for name, frame in feature_frames.items()
            if (
                config.account_profile.show_feature_tables
                or (name == "graph_features" and config.account_profile.show_graph_features)
                or (name == "anomaly_scores" and config.account_profile.show_anomaly_scores)
                or (
                    name == "account_risk_scores"
                    and config.account_profile.show_account_risk_scores
                )
            )
        }
        render_account_features(visible_features)
        st.info("Use Graph View with this account ID to inspect network context.")
        if config.enable_download_buttons:
            _download_frame(
                "Download Transactions",
                profile["transactions"],
                "account_transactions",
            )
            _download_frame("Download Alerts", profile["alerts"], "account_alerts")
            _download_frame("Download Cases", profile["cases"], "account_cases")
    except DashboardDataError as exc:
        st.info(f"Account profile data is not available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
