"""Tests for dashboard smoke CLI."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dashboard.py"


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dashboard_cli_exists_and_help_lists_commands() -> None:
    assert SCRIPT.is_file()
    result = _run_help()

    assert result.returncode == 0
    assert "config" in result.stdout
    assert "health" in result.stdout
    assert "summary" in result.stdout
    assert "graph-summary" in result.stdout
    assert "account-summary" in result.stdout
    assert "model-summary" in result.stdout
    assert "audit-summary" in result.stdout
    assert "validation-index" in result.stdout


def test_dashboard_cli_subcommand_help_exits_zero() -> None:
    for command in (
        "config",
        "health",
        "summary",
        "graph-summary",
        "account-summary",
        "model-summary",
        "audit-summary",
        "validation-index",
    ):
        assert _run_help(command).returncode == 0


def test_dashboard_graph_and_account_cli_help_lists_options() -> None:
    graph = _run_help("graph-summary")
    account = _run_help("account-summary")

    assert graph.returncode == 0
    assert "--account-id" in graph.stdout
    assert "--case-id" in graph.stdout
    assert "--community-id" in graph.stdout
    assert "--max-hops" in graph.stdout
    assert account.returncode == 0
    assert "--account-id" in account.stdout


def test_dashboard_cli_source_is_scoped_and_disposes_engine() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "dispose_dashboard_engine" in source
    forbidden = (
        "GraphDatabase.driver",
        "run_aml_rules",
        "train-score",
        "account-risk score",
        "cases.py generate",
        "cases.py risk-score",
        "evidence-build",
        "lifecycle status",
        "streamlit run",
        "graph.py load",
        "GraphDatabase.driver",
        "validate-data",
    )
    for token in forbidden:
        assert token not in source


def test_validation_index_command_does_not_create_engine() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    validation_section = source.split("def command_validation_index", maxsplit=1)[1].split(
        "def build_parser",
        maxsplit=1,
    )[0]

    assert "create_dashboard_engine" not in validation_section
