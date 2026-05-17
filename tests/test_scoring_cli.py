"""Tests for scoring CLI wiring."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scoring.py"


def run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_scoring_cli_help() -> None:
    result = run_help("--help")
    assert result.returncode == 0
    assert "account-risk" in result.stdout


def test_account_risk_score_help() -> None:
    result = run_help("account-risk", "score", "--help")
    assert result.returncode == 0
    for option in ("--persist", "--limit", "--score-version", "--score-date", "--no-artefacts"):
        assert option in result.stdout


def test_account_risk_read_and_summary_help() -> None:
    read = run_help("account-risk", "read", "--help")
    summary = run_help("account-risk", "summary", "--help")
    assert read.returncode == 0
    assert summary.returncode == 0
    assert "--latest" in read.stdout
    assert "--risk-band" in read.stdout


def test_cli_source_is_scoped() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "dispose_engine(engine)" in text
    assert "create_neo4j" not in text
    assert "run_aml_rules" not in text
    assert "isolation-forest train-score" not in text
    assert "graph.py load" not in text
    assert "generate-cases" not in text
