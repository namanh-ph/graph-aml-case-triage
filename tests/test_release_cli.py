"""CLI tests for release readiness commands."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/release.py")


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_cli_exists_and_top_help() -> None:
    assert SCRIPT.is_file()
    result = _run_help()
    assert result.returncode == 0
    assert "readiness" in result.stdout


def test_release_readiness_run_help_has_expected_options() -> None:
    result = _run_help("readiness", "run")
    assert result.returncode == 0
    for option in ("--persist", "--release-version", "--local-only", "--no-artefacts"):
        assert option in result.stdout


def test_release_read_command_help() -> None:
    for command in (
        "read-runs",
        "read-checks",
        "read-artefacts",
        "read-evidence",
        "read-portfolio",
        "summary",
    ):
        assert _run_help("readiness", command).returncode == 0


def test_release_cli_source_scope() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "dispose_engine" in text
    assert "run-pipeline" not in text
    assert "train_supervised_model" not in text
    assert "generate_labels" not in text
    assert "alter thresholds" not in text
    assert "requests." not in text
