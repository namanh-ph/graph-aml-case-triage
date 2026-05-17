"""Tests for validation report artefact readers and safe downloads."""

import json

import pandas as pd
import pytest

from graph_aml.dashboard.downloads import bytes_for_report_file
from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.validation_report_data import (
    build_validation_report_index,
    list_validation_report_files,
    read_dashboard_governance_inventory_bundle,
    read_dashboard_release_readiness_bundle,
    read_dashboard_security_control_bundle,
    read_validation_report_file,
)


def test_validation_report_listing_and_index(tmp_path) -> None:
    (tmp_path / "report.md").write_text("# Report", encoding="utf-8")
    (tmp_path / "scores.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "ignore.bin").write_bytes(b"x")

    files = list_validation_report_files(tmp_path, [".md", ".csv"])
    index = build_validation_report_index(tmp_path, [".md", ".csv"])

    assert len(files) == 2
    assert set(files["extension"]) == {".md", ".csv"}
    assert index["file_count"] == 2
    json.dumps(index, default=str)


def test_missing_report_directory_returns_empty_index(tmp_path) -> None:
    index = build_validation_report_index(tmp_path / "missing")

    assert index["file_count"] == 0


def test_validation_report_previews_and_downloads(tmp_path) -> None:
    (tmp_path / "report.md").write_text("# Report body", encoding="utf-8")
    (tmp_path / "payload.json").write_text('{"a": 1}', encoding="utf-8")
    (tmp_path / "scores.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("abcdef", encoding="utf-8")

    assert read_validation_report_file("report.md", tmp_path)["preview_text"] == "# Report body"
    assert read_validation_report_file("payload.json", tmp_path)["json"] == {"a": 1}
    csv = read_validation_report_file("scores.csv", tmp_path)
    assert csv["row_count"] == 1
    assert csv["column_count"] == 2
    preview = read_validation_report_file("notes.txt", tmp_path, max_preview_chars=3)
    assert preview["preview_text"] == "abc"
    assert bytes_for_report_file("report.md", tmp_path).startswith(b"# Report")


def test_validation_report_lists_governance_inventory_artefacts(tmp_path) -> None:
    for name in (
        "governance_inventory_report.md",
        "governance_lineage_nodes.csv",
        "governance_lineage_edges.csv",
        "governance_artefact_registry.csv",
        "governance_inventory_summary.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    files = list_validation_report_files(tmp_path, [".md", ".csv", ".json"])

    assert {
        "governance_inventory_report.md",
        "governance_lineage_nodes.csv",
        "governance_inventory_summary.json",
    } <= set(files["file_name"])


def test_validation_report_lists_security_control_artefacts(tmp_path) -> None:
    for name in (
        "security_control_report.md",
        "sensitive_field_inventory.csv",
        "security_permission_matrix.csv",
        "secrets_scan_findings.csv",
        "audit_integrity_checks.csv",
        "security_control_summary.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    files = list_validation_report_files(tmp_path, [".md", ".csv", ".json"])

    assert {
        "security_control_report.md",
        "sensitive_field_inventory.csv",
        "security_control_summary.json",
    } <= set(files["file_name"])


def test_validation_report_lists_release_readiness_artefacts(tmp_path) -> None:
    (tmp_path / "release_pack").mkdir()
    for name in (
        "release_readiness_report.md",
        "release_readiness_summary.json",
        "release_validation_index.csv",
        "release_evidence_index.csv",
        "release_pack/portfolio_summary.md",
        "release_pack/dashboard_walkthrough.md",
        "release_pack/command_transcript_template.md",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    files = list_validation_report_files(tmp_path, [".md", ".csv", ".json"])

    assert {
        "release_readiness_report.md",
        "release_readiness_summary.json",
        "portfolio_summary.md",
    } <= set(files["file_name"])


def test_dashboard_governance_inventory_bundle_reads_persisted_outputs(monkeypatch) -> None:
    run_frame = pd.DataFrame([{"inventory_run_id": "run1"}])
    empty = pd.DataFrame()
    monkeypatch.setattr(
        "graph_aml.dashboard.validation_report_data.read_inventory_runs",
        lambda *_args, **_kwargs: run_frame,
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.validation_report_data.read_governance_inventory_summary",
        lambda *_args, **_kwargs: {"latest_inventory_run_id": "run1"},
    )
    for name in (
        "read_lineage_nodes",
        "read_lineage_edges",
        "read_artefact_registry",
        "read_process_inventory",
        "read_model_inventory",
        "read_validation_inventory",
    ):
        monkeypatch.setattr(
            f"graph_aml.dashboard.validation_report_data.{name}",
            lambda *_args, **_kwargs: empty,
        )

    bundle = read_dashboard_governance_inventory_bundle(object())  # type: ignore[arg-type]

    assert bundle["summary"] == {"latest_inventory_run_id": "run1"}
    assert bundle["inventory_runs"].equals(run_frame)


def test_dashboard_security_control_bundle_reads_persisted_outputs(monkeypatch) -> None:
    run_frame = pd.DataFrame([{"security_run_id": "run1"}])
    empty = pd.DataFrame()
    monkeypatch.setattr(
        "graph_aml.dashboard.validation_report_data.read_security_control_runs",
        lambda *_args, **_kwargs: run_frame,
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.validation_report_data.read_security_control_summary",
        lambda *_args, **_kwargs: {"latest_security_run_id": "run1"},
    )
    for name in (
        "read_sensitive_field_inventory",
        "read_permission_matrix",
        "read_secrets_scan_findings",
        "read_audit_integrity_checks",
    ):
        monkeypatch.setattr(
            f"graph_aml.dashboard.validation_report_data.{name}",
            lambda *_args, **_kwargs: empty,
        )

    bundle = read_dashboard_security_control_bundle(object())  # type: ignore[arg-type]

    assert bundle["summary"] == {"latest_security_run_id": "run1"}
    assert bundle["security_runs"].equals(run_frame)


def test_dashboard_release_readiness_bundle_reads_persisted_outputs(monkeypatch) -> None:
    run_frame = pd.DataFrame([{"release_run_id": "run1"}])
    empty = pd.DataFrame()
    monkeypatch.setattr(
        "graph_aml.dashboard.validation_report_data.read_release_readiness_runs",
        lambda *_args, **_kwargs: run_frame,
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.validation_report_data.read_release_readiness_summary",
        lambda *_args, **_kwargs: {"latest_release_run_id": "run1"},
    )
    for name in (
        "read_release_repository_checks",
        "read_release_artefact_checks",
        "read_release_evidence_index",
        "read_release_portfolio_pack",
    ):
        monkeypatch.setattr(
            f"graph_aml.dashboard.validation_report_data.{name}",
            lambda *_args, **_kwargs: empty,
        )

    bundle = read_dashboard_release_readiness_bundle(object())  # type: ignore[arg-type]

    assert bundle["summary"] == {"latest_release_run_id": "run1"}
    assert bundle["release_runs"].equals(run_frame)


def test_validation_report_rejects_path_traversal(tmp_path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(DashboardDataError):
        read_validation_report_file(outside, tmp_path)
    with pytest.raises(DashboardDataError):
        bytes_for_report_file(outside, tmp_path)
