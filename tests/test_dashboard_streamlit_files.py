"""Static tests for Streamlit dashboard files."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = [
    ROOT / "app" / "streamlit_app.py",
    ROOT / "app" / "pages" / "01_Overview.py",
    ROOT / "app" / "pages" / "02_Alert_Queue.py",
    ROOT / "app" / "pages" / "03_Case_Queue.py",
    ROOT / "app" / "pages" / "04_Case_Detail.py",
    ROOT / "app" / "pages" / "05_Graph_View.py",
    ROOT / "app" / "pages" / "06_Account_Profile.py",
    ROOT / "app" / "pages" / "07_Model_Metrics.py",
    ROOT / "app" / "pages" / "08_Audit_Log.py",
    ROOT / "app" / "pages" / "09_Validation_Report.py",
]


def test_streamlit_app_and_pages_exist() -> None:
    for path in APP_FILES:
        assert path.is_file(), path


def test_streamlit_files_parse_without_syntax_errors() -> None:
    for path in APP_FILES:
        ast.parse(path.read_text(encoding="utf-8"))


def test_streamlit_sources_do_not_run_upstream_workflows() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in APP_FILES)
    forbidden = (
        "run_aml_rules",
        "train-score",
        "account-risk score",
        "cases.py generate",
        "cases.py risk-score",
        "evidence-build",
        "graph.py load",
        "docker compose",
    )

    for token in forbidden:
        assert token not in source


def test_case_detail_forms_are_guarded_by_button_clicks() -> None:
    source = (ROOT / "app" / "pages" / "04_Case_Detail.py").read_text(encoding="utf-8")

    assert "st.form_submit_button" in source
    assert "submit_dashboard_status_change" in source
    assert "submit_dashboard_assignment" in source
    assert "submit_dashboard_comment" in source


def test_graph_view_page_contains_seed_controls_and_is_read_only() -> None:
    source = (ROOT / "app" / "pages" / "05_Graph_View.py").read_text(encoding="utf-8")

    for label in ("Case ID", "Account ID", "Community ID", "Risk band", "Max hops"):
        assert label in source
    forbidden = (
        "graph.py load",
        "graph-load",
        "features-persist",
        "account-risk score",
        "cases.py generate",
        "evidence-build",
        "submit_dashboard_",
    )
    for token in forbidden:
        assert token not in source


def test_account_profile_page_contains_account_input_and_is_read_only() -> None:
    source = (ROOT / "app" / "pages" / "06_Account_Profile.py").read_text(encoding="utf-8")

    assert "Account ID" in source
    forbidden = (
        "run_aml_rules",
        "train-score",
        "account-risk score",
        "cases.py generate",
        "cases.py risk-score",
        "evidence-build",
        "graph.py load",
        "submit_dashboard_",
        "change_case_status",
        "assign_case",
        "add_case_comment",
    )
    for token in forbidden:
        assert token not in source


def test_governance_dashboard_pages_exist_and_are_read_only() -> None:
    model = (ROOT / "app" / "pages" / "07_Model_Metrics.py").read_text(encoding="utf-8")
    audit = (ROOT / "app" / "pages" / "08_Audit_Log.py").read_text(encoding="utf-8")
    validation = (ROOT / "app" / "pages" / "09_Validation_Report.py").read_text(encoding="utf-8")

    assert "Model Metrics" in model
    assert "Audit Log" in audit
    assert "Validation Report" in validation
    for token in ("train-score", "model-isolation-forest", "account-risk score", "cases.py"):
        assert token not in model
    for token in ("submit_dashboard_", "change_case_status", "assign_case", "add_case_comment"):
        assert token not in audit
    for token in ("validate-data", "generate", "train-score", "graph.py load"):
        assert token not in validation
