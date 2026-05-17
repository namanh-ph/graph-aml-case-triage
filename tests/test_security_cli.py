"""CLI tests for security controls commands."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/security.py")


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        text=True,
        capture_output=True,
        check=False,
    )


def test_security_cli_exists_and_top_help() -> None:
    assert SCRIPT.is_file()
    result = _run_help()
    assert result.returncode == 0
    assert "controls" in result.stdout
    assert "mask-preview" in result.stdout


def test_security_controls_run_help_has_expected_options() -> None:
    result = _run_help("controls", "run")
    assert result.returncode == 0
    for option in ("--persist", "--security-version", "--no-artefacts"):
        assert option in result.stdout


def test_security_read_command_help() -> None:
    for command in (
        "read-runs",
        "read-fields",
        "read-permissions",
        "read-secrets",
        "read-audit-integrity",
        "summary",
    ):
        assert _run_help("controls", command).returncode == 0
    preview = _run_help("mask-preview")
    assert preview.returncode == 0
    for option in ("--schema", "--table", "--limit"):
        assert option in preview.stdout


def test_security_cli_source_scope() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "dispose_engine" in text
    assert "run-pipeline" not in text
    assert "train_supervised_model" not in text
    assert "generate_labels" not in text
    assert "alter thresholds" not in text
    assert "requests." not in text
