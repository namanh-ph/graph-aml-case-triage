"""Tests for fan-in rule CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_fan_in_rule.py"


def test_fan_in_rule_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_fan_in_rule_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_cli_help_includes_run() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "run" in result.stdout


def test_cli_run_help_includes_expected_options() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "run", "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "--persist" in result.stdout
    assert "--limit" in result.stdout
    assert "--no-audit" in result.stdout
    assert "--min-unique-senders" in result.stdout
    assert "--window-days" in result.stdout


def test_cli_source_disposes_engine() -> None:
    assert "dispose_engine(engine)" in SCRIPT.read_text(encoding="utf-8")


def test_cli_source_calls_alert_persistence_only_when_requested() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "if args.persist" in source
    assert "persist_alerts" in source


def test_cli_source_does_not_run_unrelated_pipeline_steps() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "reset_database" not in source
    assert "initialise_database" not in source
    assert "seed_smoke_data" not in source
    assert "generate_synthetic" not in source
    assert "ingest_raw" not in source
    assert "stage_data.py" not in source
    assert "persist_account_features" not in source
    assert "run_structuring_rule(" not in source
    assert "train_model" not in source
    assert "generate_cases" not in source


def test_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
