"""Static and help tests for the model CLI."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "models.py"


def run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_models_cli_exists_and_top_level_help() -> None:
    assert SCRIPT.is_file()
    result = run_help("--help")
    assert result.returncode == 0
    assert "isolation-forest" in result.stdout
    assert "anomaly-scores" in result.stdout


def test_isolation_forest_train_score_help() -> None:
    result = run_help("isolation-forest", "train-score", "--help")
    assert result.returncode == 0
    for option in [
        "--persist",
        "--limit",
        "--no-mlflow",
        "--no-artefacts",
        "--no-graph-features",
        "--no-behavioural-features",
        "--no-jurisdiction-features",
    ]:
        assert option in result.stdout


def test_anomaly_scores_read_and_summary_help() -> None:
    read = run_help("anomaly-scores", "read", "--help")
    summary = run_help("anomaly-scores", "summary", "--help")
    assert read.returncode == 0
    assert summary.returncode == 0
    assert "--latest" in read.stdout
    assert "--risk-band" in read.stdout


def test_model_cli_source_is_scoped_and_disposes_engine() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "dispose_engine(engine)" in text
    assert "create_verified_neo4j_driver" not in text
    assert "db-reset" not in text
    assert "run_aml_rules" not in text
    assert "load_graph_from_staged" not in text
    assert "case_generation" not in text
    assert "streamlit" not in text


def test_supervised_help() -> None:
    result = run_help("supervised", "--help")
    assert result.returncode == 0
    assert "train" in result.stdout
    assert "read-scores" in result.stdout
    assert "read-runs" in result.stdout


def test_supervised_train_help() -> None:
    result = run_help("supervised", "train", "--help")
    assert result.returncode == 0
    for option in [
        "--persist",
        "--model-family",
        "--model-version",
        "--dataset-level",
        "--dataset-version",
    ]:
        assert option in result.stdout


def test_supervised_read_and_summary_help() -> None:
    assert run_help("supervised", "read-scores", "--help").returncode == 0
    assert run_help("supervised", "read-runs", "--help").returncode == 0
    assert run_help("supervised", "summary", "--help").returncode == 0


def test_supervised_cli_source_is_scoped() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "dispose_engine(engine)" in text
    assert "labels.py build" not in text
    assert "run_aml_rules" not in text
    assert "generate_synthetic" not in text
    assert "requests." not in text
