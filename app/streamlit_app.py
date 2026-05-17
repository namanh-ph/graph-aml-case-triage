"""Streamlit entry point for the local AML case triage dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardDataError,
    check_dashboard_database_health,
    create_dashboard_engine,
    dispose_dashboard_engine,
    load_dashboard_config,
)


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=config.title,
        page_icon=config.page_icon,
        layout=config.layout,
    )

    st.title(config.title)
    st.caption(
        "Local investigation workspace for persisted AML alerts, cases, evidence, "
        "and lifecycle state."
    )

    engine = None
    try:
        engine = create_dashboard_engine()
        health = check_dashboard_database_health(engine)
        st.success(f"Database health: {health.get('status', 'unknown')}")
    except DashboardDataError as exc:
        st.warning(f"Database is not ready for dashboard reads: {exc}")
    finally:
        dispose_dashboard_engine(engine)

    st.subheader("Pages")
    st.markdown(
        """
- **Overview**: portfolio counts and simple risk distributions.
- **Alert Queue**: persisted alert review queue with severity and typology filters.
- **Case Queue**: generated case queue with current status and risk filters.
- **Case Detail**: case evidence, deterministic explanation, lifecycle timeline, and guarded forms.
- **Graph View**: suspicious account, counterparty, transaction, alert, and case context.
- **Account Profile**: account/customer context, transactions, alerts, linked cases, and features.
- **Model Metrics**: model run metadata, score distributions, ranked scores, and precision@K status.
- **Audit Log**: searchable governance audit events from PostgreSQL.
- **Validation Report**: local validation artefact index and previews.
"""
    )
    st.info(
        "Prepare and persist data through the documented backend workflow before opening "
        "the dashboard. Pages read existing PostgreSQL tables and local validation artefacts."
    )
    st.markdown(
        """
Local demo preparation at a high level:

1. Start local services and reset the database.
2. Generate, load, and stage scenario data.
3. Persist alerts, graph features, anomaly scores, account risk, cases, case risk, and evidence.
4. Open the dashboard and review persisted data.
"""
    )


if __name__ == "__main__":
    main()
