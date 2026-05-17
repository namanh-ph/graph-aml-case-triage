"""Case detail page with evidence, explanation, and guarded lifecycle forms."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_aml.dashboard import (  # noqa: E402
    DashboardActionError,
    DashboardDataError,
    create_dashboard_engine,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_dashboard_case_detail,
    read_dashboard_case_evidence,
    submit_dashboard_assignment,
    submit_dashboard_comment,
    submit_dashboard_status_change,
)
from graph_aml.dashboard.components import (  # noqa: E402
    render_alert_summary,
    render_case_evidence_pack,
    render_case_explanation,
    render_case_risk_summary,
    render_case_summary,
    render_dataframe_table,
    render_lifecycle_events,
)


def _render_lifecycle_forms(engine: object, case_id: str) -> None:
    st.subheader("Lifecycle Actions")
    with st.form("status_change_form"):
        to_status = st.selectbox(
            "New status",
            [
                "In review",
                "Escalated",
                "Information requested",
                "Closed false positive",
                "Closed suspicious",
                "Archived",
            ],
        )
        analyst_id = st.text_input("Analyst ID", value="local_analyst", key="status_analyst")
        decision_reason = st.text_input("Decision reason")
        status_comment = st.text_area("Status comment")
        if st.form_submit_button("Apply Status Change"):
            try:
                result = submit_dashboard_status_change(
                    engine,  # type: ignore[arg-type]
                    case_id,
                    to_status,
                    analyst_id,
                    decision_reason=decision_reason or None,
                    comment=status_comment or None,
                )
                st.success(f"Lifecycle action persisted: {result.get('action_id')}")
            except DashboardActionError as exc:
                st.error(str(exc))

    with st.form("assignment_form"):
        assigned_to = st.text_input("Assigned to")
        assigner = st.text_input("Assigned by", value="local_analyst")
        queue = st.text_input("Queue", value="AML Review")
        assignment_comment = st.text_area("Assignment comment")
        if st.form_submit_button("Assign Case"):
            try:
                result = submit_dashboard_assignment(
                    engine,  # type: ignore[arg-type]
                    case_id,
                    assigned_to,
                    assigner,
                    queue=queue or None,
                    comment=assignment_comment or None,
                )
                st.success(f"Assignment persisted: {result.get('action_id')}")
            except DashboardActionError as exc:
                st.error(str(exc))

    with st.form("comment_form"):
        comment_analyst = st.text_input("Comment analyst", value="local_analyst")
        comment = st.text_area("Comment")
        if st.form_submit_button("Add Comment"):
            try:
                result = submit_dashboard_comment(
                    engine,  # type: ignore[arg-type]
                    case_id,
                    comment_analyst,
                    comment,
                )
                st.success(f"Comment persisted: {result.get('action_id')}")
            except DashboardActionError as exc:
                st.error(str(exc))


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Case Detail",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Case Detail")
    case_id = st.text_input("Case ID")
    if not case_id.strip():
        st.info("Enter a case ID from the Case Queue page.")
        return

    engine = None
    try:
        engine = create_dashboard_engine()
        detail = read_dashboard_case_detail(engine, case_id.strip())
        evidence = read_dashboard_case_evidence(engine, case_id.strip())
        if detail["case"].empty:
            st.info("No case was found for the supplied ID.")
            return
        render_case_summary(detail["case"].iloc[0])
        render_case_risk_summary(detail["case_risk_scores"].head(3))
        render_alert_summary(detail["alerts"].head(config.triage.case_detail_max_alerts))
        render_dataframe_table(detail["case_entities"], "Linked Entities")
        if config.enable_case_evidence_preview:
            render_case_evidence_pack(evidence["evidence_packs"])
            render_case_explanation(evidence["explanations"])
        render_lifecycle_events(
            detail["lifecycle_events"].head(config.triage.case_detail_max_lifecycle_events)
        )
        if config.enable_lifecycle_actions and engine is not None:
            _render_lifecycle_forms(engine, case_id.strip())
    except DashboardDataError as exc:
        st.info(f"Case detail data is not available yet: {exc}")
    finally:
        dispose_dashboard_engine(engine)


main()
