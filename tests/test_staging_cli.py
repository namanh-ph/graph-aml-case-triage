"""Tests for staging transformation CLI."""

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage_data.py"


def test_staging_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_staging_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_staging_cli_help_includes_stage() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "stage" in result.stdout


def test_staging_cli_help_includes_stage_options() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "--limit" in result.stdout
    assert "--no-validate" in result.stdout
    assert "--no-audit" in result.stdout


def test_staging_cli_source_disposes_engine() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "dispose_engine(engine)" in source


def test_staging_cli_source_does_not_run_unrelated_pipeline_steps() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "reset_database" not in source
    assert "initialise_database" not in source
    assert "seed_smoke_data" not in source
    assert "generate_synthetic" not in source
    assert "validate_data.py" not in source
    assert "ingest_raw.py" not in source


def test_staging_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
