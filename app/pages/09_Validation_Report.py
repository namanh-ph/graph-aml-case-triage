"""Validation Report page for local artefact browsing."""

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
    build_validation_report_index,
    bytes_for_report_file,
    create_dashboard_engine,
    dispose_dashboard_engine,
    load_dashboard_config,
    read_dashboard_governance_inventory_bundle,
    read_dashboard_release_readiness_bundle,
    read_dashboard_security_control_bundle,
    read_validation_report_file,
    render_validation_file_preview,
    render_validation_file_table,
    render_validation_report_empty_state,
    render_validation_report_index,
    safe_download_filename,
)


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(
        page_title=f"{config.title} - Validation Report",
        page_icon=config.page_icon,
        layout=config.layout,
    )
    st.title("Validation Report")
    report_config = config.validation_report
    try:
        index = build_validation_report_index(
            report_config.report_dir,
            report_config.allowed_extensions,
        )
        files = pd.DataFrame(index.get("files", []))
        if files.empty:
            render_validation_report_empty_state(report_config.report_dir)
            return
        render_validation_report_index(index)
        governance_files = files[
            files["relative_path"]
            .astype(str)
            .isin(
                [
                    "governance_inventory_report.md",
                    "governance_lineage_nodes.csv",
                    "governance_lineage_edges.csv",
                    "governance_artefact_registry.csv",
                    "governance_inventory_summary.json",
                ]
            )
        ]
        security_files = files[
            files["relative_path"]
            .astype(str)
            .isin(
                [
                    "security_control_report.md",
                    "sensitive_field_inventory.csv",
                    "security_permission_matrix.csv",
                    "secrets_scan_findings.csv",
                    "audit_integrity_checks.csv",
                    "security_control_summary.json",
                ]
            )
        ]
        release_files = files[
            files["relative_path"]
            .astype(str)
            .isin(
                [
                    "release_readiness_report.md",
                    "release_readiness_summary.json",
                    "release_validation_index.csv",
                    "release_evidence_index.csv",
                    "release_pack/portfolio_summary.md",
                    "release_pack/dashboard_walkthrough.md",
                    "release_pack/command_transcript_template.md",
                ]
            )
        ]
        engine = None
        try:
            engine = create_dashboard_engine()
            governance_bundle = read_dashboard_governance_inventory_bundle(engine)
            governance_summary = governance_bundle.get("summary", {})
            if isinstance(governance_summary, dict) and governance_summary.get(
                "latest_inventory_run_id"
            ):
                st.subheader("Persisted Governance Inventory")
                columns = st.columns(6)
                metrics = [
                    ("Run", governance_summary.get("latest_inventory_run_id")),
                    ("Nodes", governance_summary.get("lineage_node_count")),
                    ("Edges", governance_summary.get("lineage_edge_count")),
                    ("Artefacts", governance_summary.get("artefact_count")),
                    ("Processes", governance_summary.get("process_count")),
                    ("Models", governance_summary.get("model_inventory_count")),
                ]
                for column, (label, value) in zip(columns, metrics, strict=False):
                    column.metric(label, value if value is not None else "-")
                st.metric(
                    "Validations",
                    governance_summary.get("validation_inventory_count", "-"),
                )
                for label, key in (
                    ("Lineage Nodes", "lineage_nodes"),
                    ("Lineage Edges", "lineage_edges"),
                    ("Artefact Registry", "artefact_registry"),
                    ("Process Inventory", "process_inventory"),
                    ("Model Inventory", "model_inventory"),
                    ("Validation Inventory", "validation_inventory"),
                ):
                    frame = governance_bundle.get(key)
                    if isinstance(frame, pd.DataFrame) and not frame.empty:
                        with st.expander(label):
                            st.dataframe(frame, use_container_width=True)
            security_bundle = read_dashboard_security_control_bundle(engine)
            security_summary = security_bundle.get("summary", {})
            if isinstance(security_summary, dict) and security_summary.get(
                "latest_security_run_id"
            ):
                st.subheader("Persisted Security Controls")
                columns = st.columns(5)
                metrics = [
                    ("Run", security_summary.get("latest_security_run_id")),
                    ("Fields", security_summary.get("sensitive_field_count")),
                    ("Restricted", security_summary.get("restricted_field_count")),
                    ("Secrets", security_summary.get("unallowed_secrets_count")),
                    ("Audit Issues", security_summary.get("audit_integrity_issue_count")),
                ]
                for column, (label, value) in zip(columns, metrics, strict=False):
                    column.metric(label, value if value is not None else "-")
                st.metric("Permissions", security_summary.get("permission_row_count", "-"))
                for label, key in (
                    ("Sensitive Fields", "sensitive_fields"),
                    ("Permission Matrix", "permission_matrix"),
                    ("Secrets Scan", "secrets_scan"),
                    ("Audit Integrity", "audit_integrity"),
                ):
                    frame = security_bundle.get(key)
                    if isinstance(frame, pd.DataFrame) and not frame.empty:
                        with st.expander(label):
                            st.dataframe(frame, use_container_width=True)
            release_bundle = read_dashboard_release_readiness_bundle(engine)
            release_summary = release_bundle.get("summary", {})
            if isinstance(release_summary, dict) and release_summary.get(
                "latest_release_run_id"
            ):
                st.subheader("Persisted Release Readiness")
                columns = st.columns(5)
                metrics = [
                    ("Run", release_summary.get("latest_release_run_id")),
                    ("Failed", release_summary.get("failed_check_count")),
                    ("Warnings", release_summary.get("warning_check_count")),
                    ("Artefacts", release_summary.get("validation_artefact_count")),
                    ("Evidence", release_summary.get("evidence_item_count")),
                ]
                for column, (label, value) in zip(columns, metrics, strict=False):
                    column.metric(label, value if value is not None else "-")
                for label, key in (
                    ("Repository Checks", "repository_checks"),
                    ("Artefact Checks", "artefact_checks"),
                    ("Evidence Index", "evidence_index"),
                    ("Portfolio Pack", "portfolio_pack"),
                ):
                    frame = release_bundle.get(key)
                    if isinstance(frame, pd.DataFrame) and not frame.empty:
                        with st.expander(label):
                            st.dataframe(frame, use_container_width=True)
        except DashboardDataError:
            pass
        finally:
            dispose_dashboard_engine(engine)
        if not governance_files.empty:
            st.subheader("Governance Inventory")
            summary_rows = governance_files[
                governance_files["relative_path"].astype(str) == "governance_inventory_summary.json"
            ]
            if not summary_rows.empty:
                summary_preview = read_validation_report_file(
                    "governance_inventory_summary.json",
                    report_config.report_dir,
                    report_config.max_preview_chars,
                )
                summary_json = summary_preview.get("json")
                if isinstance(summary_json, dict):
                    summary = summary_json.get("summary", {})
                    if isinstance(summary, dict):
                        columns = st.columns(6)
                        metrics = [
                            ("Run", summary.get("inventory_run_id")),
                            ("Nodes", summary.get("lineage_node_count")),
                            ("Edges", summary.get("lineage_edge_count")),
                            ("Artefacts", summary.get("artefact_count")),
                            ("Processes", summary.get("process_count")),
                            ("Models", summary.get("model_inventory_count")),
                        ]
                        for column, (label, value) in zip(columns, metrics, strict=False):
                            column.metric(label, value if value is not None else "-")
                        st.metric(
                            "Validations",
                            summary.get("validation_inventory_count", "-"),
                        )
            render_validation_file_table(governance_files)
        if not security_files.empty:
            st.subheader("Security Controls")
            summary_rows = security_files[
                security_files["relative_path"].astype(str) == "security_control_summary.json"
            ]
            if not summary_rows.empty:
                summary_preview = read_validation_report_file(
                    "security_control_summary.json",
                    report_config.report_dir,
                    report_config.max_preview_chars,
                )
                summary_json = summary_preview.get("json")
                if isinstance(summary_json, dict):
                    summary = summary_json.get("summary", {})
                    if isinstance(summary, dict):
                        columns = st.columns(5)
                        metrics = [
                            ("Run", summary.get("security_run_id")),
                            ("Fields", summary.get("sensitive_field_count")),
                            ("Restricted", summary.get("restricted_field_count")),
                            ("Secrets", summary.get("unallowed_secret_finding_count")),
                            ("Audit Issues", summary.get("audit_integrity_issue_count")),
                        ]
                        for column, (label, value) in zip(columns, metrics, strict=False):
                            column.metric(label, value if value is not None else "-")
            render_validation_file_table(security_files)
        if not release_files.empty:
            st.subheader("Release Readiness")
            summary_rows = release_files[
                release_files["relative_path"].astype(str) == "release_readiness_summary.json"
            ]
            if not summary_rows.empty:
                summary_preview = read_validation_report_file(
                    "release_readiness_summary.json",
                    report_config.report_dir,
                    report_config.max_preview_chars,
                )
                summary_json = summary_preview.get("json")
                if isinstance(summary_json, dict):
                    summary = summary_json.get("summary", {})
                    if isinstance(summary, dict):
                        columns = st.columns(5)
                        metrics = [
                            ("Run", summary.get("release_run_id")),
                            ("Failed", summary.get("failed_check_count")),
                            ("Warnings", summary.get("warning_check_count")),
                            ("Artefacts", summary.get("validation_artefact_count")),
                            ("Evidence", summary.get("evidence_item_count")),
                        ]
                        for column, (label, value) in zip(columns, metrics, strict=False):
                            column.metric(label, value if value is not None else "-")
            render_validation_file_table(release_files)
        render_validation_file_table(files)
        selected = st.selectbox("Validation artefact", files["relative_path"].astype(str).tolist())
        preview = read_validation_report_file(
            selected,
            report_config.report_dir,
            report_config.max_preview_chars,
        )
        render_validation_file_preview(preview)
        if report_config.show_downloads:
            st.download_button(
                "Download Artefact",
                bytes_for_report_file(selected, report_config.report_dir),
                file_name=safe_download_filename(Path(selected).stem, Path(selected).suffix[1:]),
            )
    except DashboardDataError as exc:
        st.info(f"Validation report artefacts are not available: {exc}")


main()
