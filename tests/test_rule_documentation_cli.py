"""Static tests for AML rule documentation CLI."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_rule_documentation.py"


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_rule_documentation_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_rule_documentation_cli_help_exits_successfully() -> None:
    result = _run_help()

    assert result.returncode == 0
    assert "list" in result.stdout
    assert "validate" in result.stdout
    assert "generate" in result.stdout


def test_rule_documentation_subcommand_help_exits_successfully() -> None:
    for command in ("list", "validate", "generate"):
        result = _run_help(command)
        assert result.returncode == 0


def test_generate_help_includes_output_options() -> None:
    result = _run_help("generate")

    assert "--rules" in result.stdout
    assert "--docs-output-dir" in result.stdout
    assert "--reports-output-dir" in result.stdout


def test_cli_source_does_not_create_database_engine_or_persist_alerts() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "create_database_engine" not in source
    assert "run_rule_engine" not in source
    assert "run_structuring_rule" not in source
    assert "persist_alerts" not in source
    assert "persist_alert_records" not in source


def test_cli_source_configures_logging_only_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "configure_logging(" in source
    assert "def _configure_logging()" in source
    assert source.index("def _configure_logging()") < source.index("configure_logging(")
