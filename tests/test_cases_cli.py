"""Tests for the case generation CLI surface."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/cases.py")


def run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cases_cli_exists_and_top_level_help() -> None:
    assert SCRIPT.exists()
    result = run_help("--help")
    assert result.returncode == 0
    assert "generate" in result.stdout
    assert "read" in result.stdout
    assert "detail" in result.stdout
    assert "summary" in result.stdout
    assert "risk-score" in result.stdout
    assert "risk-read" in result.stdout
    assert "risk-summary" in result.stdout
    assert "evidence-build" in result.stdout
    assert "evidence-read" in result.stdout
    assert "evidence-summary" in result.stdout
    assert "lifecycle" in result.stdout


def test_cases_generate_help_includes_expected_options() -> None:
    result = run_help("generate", "--help")
    assert result.returncode == 0
    for option in ("--persist", "--limit", "--case-version", "--no-artefacts"):
        assert option in result.stdout


def test_cases_read_detail_and_summary_help() -> None:
    read = run_help("read", "--help")
    detail = run_help("detail", "--help")
    summary = run_help("summary", "--help")
    assert read.returncode == detail.returncode == summary.returncode == 0
    assert "--status" in read.stdout
    assert "--severity" in read.stdout
    assert "--account-id" in read.stdout
    assert "--case-id" in detail.stdout


def test_case_risk_cli_help() -> None:
    risk_score = run_help("risk-score", "--help")
    risk_read = run_help("risk-read", "--help")
    risk_summary = run_help("risk-summary", "--help")
    assert risk_score.returncode == risk_read.returncode == risk_summary.returncode == 0
    for option in (
        "--persist",
        "--limit",
        "--score-version",
        "--no-artefacts",
        "--no-case-snapshot",
    ):
        assert option in risk_score.stdout
    assert "--latest" in risk_read.stdout
    assert "--risk-band" in risk_read.stdout


def test_case_evidence_cli_help() -> None:
    evidence_build = run_help("evidence-build", "--help")
    evidence_read = run_help("evidence-read", "--help")
    evidence_summary = run_help("evidence-summary", "--help")
    assert evidence_build.returncode == evidence_read.returncode == evidence_summary.returncode == 0
    for option in (
        "--persist",
        "--case-id",
        "--limit",
        "--evidence-version",
        "--explanation-version",
        "--no-artefacts",
    ):
        assert option in evidence_build.stdout
    assert "--case-id" in evidence_read.stdout


def test_case_lifecycle_cli_help() -> None:
    lifecycle = run_help("lifecycle", "--help")
    status = run_help("lifecycle", "status", "--help")
    assign = run_help("lifecycle", "assign", "--help")
    comment = run_help("lifecycle", "comment", "--help")
    events = run_help("lifecycle", "events", "--help")
    assignments = run_help("lifecycle", "assignments", "--help")
    summary = run_help("lifecycle", "summary", "--help")
    assert lifecycle.returncode == 0
    assert status.returncode == assign.returncode == comment.returncode == 0
    assert events.returncode == assignments.returncode == summary.returncode == 0
    for option in ("--case-id", "--to-status", "--analyst-id", "--decision-reason", "--no-audit"):
        assert option in status.stdout
    for option in ("--case-id", "--assigned-to", "--queue", "--no-audit"):
        assert option in assign.stdout
    assert "--case-id" in comment.stdout
    assert "--comment" in comment.stdout
    for option in ("--case-id", "--analyst-id", "--action-type", "--write-artefacts"):
        assert option in events.stdout
    assert "--assigned-to" in assignments.stdout
    assert "--queue" in assignments.stdout


def test_cases_cli_source_closes_resources_and_avoids_forbidden_workflows() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "dispose_engine(engine)" in source
    assert "neo4j" not in source.lower()
    forbidden = (
        "run_aml_rules",
        "train-score",
        "account-risk score",
        "graph-load",
        "streamlit",
    )
    for token in forbidden:
        assert token not in source
