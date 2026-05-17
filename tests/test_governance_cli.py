"""CLI tests for governance inventory commands."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/governance.py")


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        text=True,
        capture_output=True,
        check=False,
    )


def test_governance_cli_exists_and_top_help() -> None:
    assert SCRIPT.is_file()
    result = _run_help()
    assert result.returncode == 0
    assert "inventory" in result.stdout


def test_governance_inventory_run_help_has_expected_options() -> None:
    result = _run_help("inventory", "run")
    assert result.returncode == 0
    for option in ("--persist", "--inventory-version", "--no-artefacts"):
        assert option in result.stdout


def test_governance_inventory_read_command_help() -> None:
    for command in (
        "read-runs",
        "read-lineage",
        "read-artefacts",
        "read-processes",
        "read-models",
        "read-validations",
        "summary",
    ):
        assert _run_help("inventory", command).returncode == 0


def test_governance_cli_source_scope() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "dispose_engine" in text
    assert "run-pipeline" not in text
    assert "train_supervised_model" not in text
    assert "generate_labels" not in text
    assert "alter thresholds" not in text
    assert "requests." not in text
