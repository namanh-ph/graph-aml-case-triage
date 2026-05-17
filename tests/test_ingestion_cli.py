"""Tests for the raw ingestion CLI script."""

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ingest_raw.py"


def test_ingestion_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_ingestion_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_ingestion_cli_help_includes_commands() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "ingest" in result.stdout
    assert "ingest-latest" in result.stdout


def test_ingestion_cli_help_includes_source_options() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "--metadata-path" in result.stdout
    assert "--dataset-id" in result.stdout
    assert "--no-audit" in result.stdout


def test_ingestion_cli_source_disposes_engine() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "dispose_engine(engine)" in source


def test_ingestion_cli_source_does_not_manage_database_lifecycle() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "reset_database" not in source
    assert "initialise_database" not in source
    assert "seed_smoke_data" not in source


def test_ingestion_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
