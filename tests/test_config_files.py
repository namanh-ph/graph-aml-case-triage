"""Structural tests for declarative YAML configuration files."""

from collections.abc import Mapping
from math import isclose
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

EXPECTED_CONFIG_KEYS: dict[str, set[str]] = {
    "project.yaml": {"project", "runtime", "governance"},
    "paths.yaml": {"paths", "files"},
    "database.yaml": {"postgres", "schemas", "tables"},
    "neo4j.yaml": {"neo4j", "graph"},
    "rules.yaml": {"rules"},
    "scoring.yaml": {"scoring", "account_risk_score", "case_risk_score"},
    "model.yaml": {"model", "features", "isolation_forest", "evaluation"},
    "dashboard.yaml": {"dashboard", "pages", "tables", "charts", "filters"},
}


def load_config(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{filename} must parse to a dictionary"
    return loaded


def test_expected_config_files_exist() -> None:
    for filename in EXPECTED_CONFIG_KEYS:
        assert (CONFIG_DIR / filename).is_file(), f"Missing config file: {filename}"


def test_config_files_parse_to_dictionaries() -> None:
    for filename in EXPECTED_CONFIG_KEYS:
        loaded = load_config(filename)
        assert loaded, f"{filename} must not be empty"


def test_required_top_level_keys_exist() -> None:
    for filename, required_keys in EXPECTED_CONFIG_KEYS.items():
        loaded = load_config(filename)
        assert required_keys <= set(loaded), f"{filename} missing required keys"


def test_account_risk_weights_sum_to_one() -> None:
    scoring = load_config("scoring.yaml")
    weights = scoring["account_risk_score"]["weights"]

    assert isinstance(weights, Mapping)
    assert isclose(sum(weights.values()), 1.0)


def test_case_risk_weights_sum_to_one() -> None:
    scoring = load_config("scoring.yaml")
    weights = scoring["case_risk_score"]["weights"]

    assert isinstance(weights, Mapping)
    assert isclose(sum(weights.values()), 1.0)


def test_rule_severity_bands_are_complete() -> None:
    rules = load_config("rules.yaml")
    severity_bands = rules["rules"]["severity_bands"]

    assert {"low", "medium", "high", "critical"} <= set(severity_bands)


def test_dashboard_pages_include_expected_titles() -> None:
    dashboard = load_config("dashboard.yaml")
    page_titles = {page["title"] for page in dashboard["pages"].values()}

    assert {
        "Overview",
        "Alert Queue",
        "Case Detail",
        "Graph View",
        "Account Profile",
        "Model Metrics",
        "Audit Log",
        "Validation Report",
    } <= page_titles


def test_env_example_contains_referenced_environment_variables() -> None:
    database = load_config("database.yaml")
    neo4j = load_config("neo4j.yaml")
    model = load_config("model.yaml")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    referenced_env_vars = {
        database["postgres"]["host_env"],
        database["postgres"]["port_env"],
        database["postgres"]["database_env"],
        database["postgres"]["user_env"],
        database["postgres"]["password_env"],
        neo4j["neo4j"]["uri_env"],
        neo4j["neo4j"]["user_env"],
        neo4j["neo4j"]["password_env"],
        model["mlflow"]["tracking_uri_env"],
    }

    for env_var in referenced_env_vars:
        assert f"{env_var}=" in env_example
