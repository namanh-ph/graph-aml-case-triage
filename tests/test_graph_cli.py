"""Static tests for Neo4j graph utility CLI."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "graph.py"


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_graph_cli_exists() -> None:
    assert SCRIPT.is_file()


def test_graph_cli_help_exits_successfully() -> None:
    result = _run_help()

    assert result.returncode == 0
    assert "config" in result.stdout
    assert "health" in result.stdout
    assert "constraints-list" in result.stdout
    assert "constraints-ensure" in result.stdout
    assert "load" in result.stdout
    assert "analytics" in result.stdout
    assert "features-persist" in result.stdout
    assert "features-read" in result.stdout
    assert "features-summary" in result.stdout


def test_graph_subcommand_help_exits_successfully() -> None:
    for command in ("config", "health", "constraints-list", "constraints-ensure"):
        result = _run_help(command)
        assert result.returncode == 0
        assert "--config" in result.stdout
        assert "--database" in result.stdout


def test_graph_load_help_includes_load_options() -> None:
    result = _run_help("load")

    assert result.returncode == 0
    for option in (
        "--limit",
        "--no-alerts",
        "--no-constraints",
        "--batch-size",
        "--output-dir",
        "--no-artefacts",
        "--no-reconcile",
    ):
        assert option in result.stdout


def test_graph_analytics_help_includes_analytics_options() -> None:
    result = _run_help("analytics")

    assert result.returncode == 0
    for option in (
        "--output-dir",
        "--no-artefacts",
        "--max-shortest-path-depth",
        "--pagerank-alpha",
        "--betweenness-sample-size",
        "--community-algorithm",
        "--cycle-max-hops",
        "--exclude-counterparties",
        "--exclude-alert-nodes",
        "--exclude-transaction-nodes",
    ):
        assert option in result.stdout


def test_graph_feature_persistence_help_includes_options() -> None:
    result = _run_help("features-persist")

    assert result.returncode == 0
    for option in (
        "--feature-date",
        "--feature-version",
        "--graph-build-id",
        "--batch-size",
        "--no-audit",
        "--no-artefacts",
    ):
        assert option in result.stdout


def test_graph_feature_read_and_summary_help_exits_successfully() -> None:
    read_result = _run_help("features-read")
    summary_result = _run_help("features-summary")

    assert read_result.returncode == 0
    assert "--latest" in read_result.stdout
    assert summary_result.returncode == 0


def test_graph_cli_source_does_not_print_password_value() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "config.password" not in source
    assert "print(password" not in source


def test_graph_cli_source_disposes_driver() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "close_neo4j_driver(driver)" in source
    assert "dispose_engine(postgres_engine)" in source


def test_graph_analytics_source_closes_driver_and_does_not_use_postgres() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    analytics_source = source[
        source.index("def command_analytics") : source.index("def _feature_date_from_arg")
    ]

    assert "close_neo4j_driver(driver)" in analytics_source
    assert "create_database_engine" not in analytics_source
    assert "dispose_engine" not in analytics_source
    assert "persist" not in analytics_source


def test_graph_feature_cli_lifecycle_and_connection_scope() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    persist_source = source[
        source.index("def command_features_persist") : source.index("def command_features_read")
    ]
    read_source = source[
        source.index("def command_features_read") : source.index("def command_features_summary")
    ]
    summary_source = source[
        source.index("def command_features_summary") : source.index("def _feature_fail")
    ]

    assert "dispose_engine(postgres_engine)" in persist_source
    assert "close_neo4j_driver(driver)" in persist_source
    assert "create_verified_neo4j_driver" not in read_source
    assert "create_verified_neo4j_driver" not in summary_source


def test_graph_cli_source_does_not_run_unrelated_workflows_or_delete_graph_data() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "scripts/db.py" not in source
    assert "run_aml_rules" not in source
    assert "run_rule_engine" not in source
    assert "DETACH DELETE" not in source
    assert "DELETE FROM" not in source
    assert "train-model" not in source
    assert "generate-cases" not in source
    assert "dashboard" not in source


def test_graph_cli_source_configures_logging_only_inside_cli_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "configure_logging(" in source
    assert "def _configure_logging()" in source
    assert source.index("def _configure_logging()") < source.index("configure_logging(")
