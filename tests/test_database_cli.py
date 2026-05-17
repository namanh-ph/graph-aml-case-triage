"""Tests for the database CLI script structure."""

import sys
from importlib import import_module
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
DB_SCRIPT = ROOT / "scripts" / "db.py"


def test_database_cli_script_exists() -> None:
    assert DB_SCRIPT.is_file()


def test_database_cli_help_exits_zero() -> None:
    result = run(
        [sys.executable, str(DB_SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    assert result.returncode == 0


def test_database_cli_help_includes_commands() -> None:
    result = run(
        [sys.executable, str(DB_SCRIPT), "--help"],
        capture_output=True,
        check=False,
        cwd=ROOT,
        text=True,
    )

    for command in (
        "check",
        "version",
        "list-schemas",
        "list-tables",
        "init",
        "reset",
        "seed-smoke",
        "delete-smoke-seed",
    ):
        assert command in result.stdout


def test_database_cli_source_requires_confirmation_for_reset() -> None:
    source = DB_SCRIPT.read_text(encoding="utf-8")

    assert 'subparsers.add_parser("reset"' in source
    assert 'reset.add_argument("--yes"' in source
    assert "Database reset refused" in source


def test_database_cli_source_requires_confirmation_for_smoke_seed_deletion() -> None:
    source = DB_SCRIPT.read_text(encoding="utf-8")

    assert 'subparsers.add_parser(\n        "delete-smoke-seed"' in source
    assert 'delete_seed.add_argument("--yes"' in source
    assert "Smoke seed deletion refused" in source


def test_database_cli_source_disposes_engine() -> None:
    source = DB_SCRIPT.read_text(encoding="utf-8")

    assert "dispose_engine(engine)" in source


def test_database_cli_can_be_imported_without_connection() -> None:
    module = import_module("scripts.db")

    assert hasattr(module, "build_parser")


def test_database_cli_source_has_no_automatic_reset_or_seed_on_import() -> None:
    source = DB_SCRIPT.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert source.rstrip().endswith("raise SystemExit(main())")
