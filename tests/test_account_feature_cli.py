"""Tests for account feature generation CLI."""

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_account_features.py"


def test_account_feature_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_account_feature_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_cli_help_includes_staged() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "staged" in result.stdout


def test_cli_help_includes_expected_options() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "--limit" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--feature-version" in result.stdout
    assert "--min-feature-date" in result.stdout
    assert "--max-feature-date" in result.stdout
    assert "--extended" in result.stdout
    assert "--reporting-threshold" in result.stdout
    assert "--below-threshold-margin" in result.stdout
    assert "--entropy-window-days" in result.stdout
    assert "--jurisdiction-window-days" in result.stdout
    assert "--persist" in result.stdout
    assert "--no-audit" in result.stdout
    assert "--read-mart" in result.stdout
    assert "--feature-version-filter" in result.stdout


def test_cli_source_disposes_engine() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "dispose_engine(engine)" in source


def test_cli_source_does_not_run_unrelated_pipeline_steps() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "reset_database" not in source
    assert "initialise_database" not in source
    assert "seed_smoke_data" not in source
    assert "generate_synthetic" not in source
    assert "ingest_raw.py" not in source
    assert "stage_data.py" not in source


def test_cli_source_calls_extended_generation_when_extended_is_provided() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "if args.extended" in source
    assert "calculate_extended_account_features" in source
    assert "read_staged_extended_feature_inputs" in source


def test_cli_source_calls_persistence_when_persist_is_provided() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "if args.persist" in source
    assert "persist_account_features" in source


def test_cli_source_calls_mart_readers_when_read_mart_is_provided() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "if args.read_mart" in source
    assert "read_mart_account_features" in source
    assert "get_mart_account_feature_versions" in source


def test_cli_source_does_not_run_destructive_commands_or_model_training() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "db-reset" not in source
    assert "reset_database" not in source
    assert "run_aml" not in source
    assert "train_model" not in source
    assert "mlflow" not in source


def test_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
