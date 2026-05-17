"""Tests for circular flow detection CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "detect_circular_flows.py"


def test_circular_flow_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_circular_flow_cli_help_exits_zero() -> None:
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

    assert "--limit" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--no-artefacts" in result.stdout
    assert "--no-audit" in result.stdout
    assert "--max-cycle-hops" in result.stdout
    assert "--min-cycle-hops" in result.stdout
    assert "--min-total-amount" in result.stdout
    assert "--max-time-span-hours" in result.stdout
    assert "--include-counterparty-edges" in result.stdout
    assert "--include-self-loops" in result.stdout


def test_cli_source_disposes_engine() -> None:
    assert "dispose_engine(engine)" in SCRIPT.read_text(encoding="utf-8")


def test_cli_source_does_not_call_alert_persistence() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "persist_alerts" not in source
    assert "alerts_upserted" not in source


def test_detection_only_cli_does_not_call_alert_construction() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "build_circular_flow_alerts" not in source
    assert "run_circular_flow_rule" not in source
    assert "run_circular_flow_detection_and_alerts" not in source


def test_detection_only_cli_still_supports_no_artefacts() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "--no-artefacts" in source


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
    assert "run_fan_in_rule(" not in source
    assert "run_fan_out_rule(" not in source
    assert "run_rapid_movement_rule(" not in source
    assert "run_dormant_reactivation_rule(" not in source
    assert "train_model" not in source
    assert "generate_cases" not in source


def test_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
