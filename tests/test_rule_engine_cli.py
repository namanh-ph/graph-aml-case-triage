"""Static CLI tests for the unified AML rule runner."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_aml_rules.py"


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_run_aml_rules_script_exists() -> None:
    assert SCRIPT.is_file()


def test_top_level_help_exits_zero() -> None:
    assert _run_help("--help").returncode == 0


def test_cli_help_includes_list_and_run() -> None:
    output = _run_help("--help").stdout

    assert "list" in output
    assert "run" in output


def test_list_help_exits_zero() -> None:
    assert _run_help("list", "--help").returncode == 0


def test_run_help_includes_rules_option() -> None:
    assert "--rules" in _run_help("run", "--help").stdout


def test_run_help_includes_exclude_rules_option() -> None:
    assert "--exclude-rules" in _run_help("run", "--help").stdout


def test_run_help_includes_persist_option() -> None:
    assert "--persist" in _run_help("run", "--help").stdout


def test_run_help_includes_no_audit_option() -> None:
    assert "--no-audit" in _run_help("run", "--help").stdout


def test_run_help_includes_no_engine_audit_option() -> None:
    assert "--no-engine-audit" in _run_help("run", "--help").stdout


def test_run_help_includes_no_artefacts_option() -> None:
    assert "--no-artefacts" in _run_help("run", "--help").stdout


def test_run_help_includes_limit_option() -> None:
    assert "--limit" in _run_help("run", "--help").stdout


def test_run_help_includes_output_dir_option() -> None:
    assert "--output-dir" in _run_help("run", "--help").stdout


def test_cli_source_disposes_engine() -> None:
    assert "dispose_engine(engine)" in SCRIPT.read_text(encoding="utf-8")


def test_cli_source_does_not_run_unrelated_workflows() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    forbidden = (
        "reset_database",
        "initialise",
        "seed_smoke",
        "generate_cases",
        "persist_account_features",
        "train_model",
    )
    for text in forbidden:
        assert text not in source


def test_cli_source_configures_logging_only_inside_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _configure_logging" in source
    assert "configure_logging(" in source
    assert source.index("configure_logging(") > source.index("def _configure_logging")
