from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "labels.py"


def _help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_labels_cli_exists() -> None:
    assert SCRIPT.exists()


def test_labels_cli_help_exits_zero() -> None:
    result = _help()
    assert result.returncode == 0
    assert "build" in result.stdout
    assert "read" in result.stdout
    assert "summary" in result.stdout


def test_build_help_includes_options() -> None:
    stdout = _help("build").stdout
    assert "--persist" in stdout
    assert "--limit" in stdout
    assert "--label-version" in stdout
    assert "--dataset-version" in stdout


def test_read_help_exits_zero() -> None:
    assert _help("read").returncode == 0


def test_summary_help_exits_zero() -> None:
    assert _help("summary").returncode == 0


def test_cli_source_disposes_postgresql_engine() -> None:
    assert "dispose_dashboard_engine(engine)" in SCRIPT.read_text(encoding="utf-8")


def test_cli_source_does_not_train_models() -> None:
    text = SCRIPT.read_text(encoding="utf-8").lower()
    assert "train-score" not in text
    assert "fit(" not in text


def test_cli_source_does_not_mutate_lifecycle_decisions() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "lifecycle status" not in text


def test_cli_source_does_not_run_upstream_workflows() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    forbidden = ("run-aml-rules", "graph-load", "case-risk-score", "demo-run")
    assert all(value not in text for value in forbidden)
