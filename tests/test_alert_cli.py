"""Tests for alert schema CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alerts.py"


def test_alert_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_alert_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_cli_help_includes_schema_info_and_read() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "schema-info" in result.stdout
    assert "read" in result.stdout


def test_cli_read_help_includes_filters() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "read", "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "--rule-name" in result.stdout
    assert "--severity" in result.stdout
    assert "--status" in result.stdout
    assert "--limit" in result.stdout


def test_cli_source_disposes_engine() -> None:
    assert "dispose_engine(engine)" in SCRIPT.read_text(encoding="utf-8")


def test_cli_source_does_not_run_aml_rules() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "run-rules" not in source
    assert "detect_structuring" not in source


def test_cli_source_does_not_persist_alerts() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "upsert_alerts" not in source
    assert "persist_alerts" not in source


def test_cli_source_does_not_run_unrelated_pipeline_steps() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "reset_database" not in source
    assert "initialise_database" not in source
    assert "seed_smoke_data" not in source
    assert "generate_synthetic" not in source
    assert "ingest_raw" not in source
    assert "stage_data" not in source
    assert "persist_account_features" not in source
    assert "train_model" not in source
    assert "generate_cases" not in source


def test_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
