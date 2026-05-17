"""Tests for the data dictionary CLI."""

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_data_dictionary.py"


def test_data_dictionary_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_data_dictionary_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_data_dictionary_cli_help_includes_generate() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "generate" in result.stdout


def test_data_dictionary_cli_help_includes_output_dir() -> None:
    result = run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert "--output-dir" in result.stdout


def test_data_dictionary_cli_can_generate_artefacts(tmp_path: Path) -> None:
    result = run(
        [
            sys.executable,
            str(SCRIPT),
            "generate",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "feature_dictionary.md").is_file()
    assert (tmp_path / "data_dictionary.json").is_file()
    assert (tmp_path / "data_dictionary.csv").is_file()


def test_data_dictionary_cli_source_does_not_connect_to_postgresql() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "create_database_engine" not in source
    assert "psycopg" not in source
    assert "sqlalchemy" not in source


def test_data_dictionary_cli_configures_logging_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert "enable_console=False" in source
