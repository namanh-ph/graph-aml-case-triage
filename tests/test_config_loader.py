"""Tests for typed configuration loading and validation."""

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from graph_aml.config.exceptions import ConfigFileNotFoundError, ConfigValidationError
from graph_aml.config.loader import load_app_config, load_config_dict, load_yaml_file
from graph_aml.config.schemas import AppConfig


def test_load_yaml_file_loads_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "valid.yaml"
    path.write_text("section:\n  value: 1\n", encoding="utf-8")

    assert load_yaml_file(path) == {"section": {"value": 1}}


def test_load_yaml_file_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileNotFoundError):
        load_yaml_file(tmp_path / "missing.yaml")


def test_load_yaml_file_raises_for_list_root(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(ConfigValidationError):
        load_yaml_file(path)


def test_load_config_dict_returns_all_aggregate_keys() -> None:
    config_dict = load_config_dict()

    assert set(config_dict) == {
        "project",
        "paths",
        "database",
        "neo4j",
        "rules",
        "scoring",
        "model",
        "dashboard",
    }


def test_load_app_config_returns_app_config() -> None:
    config = load_app_config()

    assert isinstance(config, AppConfig)


def test_loaded_app_config_exposes_expected_values() -> None:
    config = load_app_config()

    assert config.project.project.name == "graph-aml-case-triage"
    assert config.project.project.package_name == "graph_aml"
    assert config.database.postgres.defaults.database == "graph_aml"
    assert config.neo4j.neo4j.defaults.uri == "bolt://localhost:7687"
    assert config.rules.rules.structuring.reporting_threshold == 10000
    assert config.scoring.account_risk_score.weights["rule_typology_score"] == 0.35
    assert config.model.isolation_forest.n_estimators == 200
    assert config.dashboard.dashboard.app_title == "Graph-Based AML Case Triage"


def test_account_risk_weights_sum_to_one() -> None:
    config = load_app_config()

    assert abs(sum(config.scoring.account_risk_score.weights.values()) - 1.0) <= 1e-9


def test_case_risk_weights_sum_to_one() -> None:
    config = load_app_config()

    assert abs(sum(config.scoring.case_risk_score.weights.values()) - 1.0) <= 1e-9


def test_invalid_scoring_weights_raise_validation_error() -> None:
    config_dict = deepcopy(load_config_dict())
    config_dict["scoring"]["account_risk_score"]["weights"]["anomaly_score"] = 0.99

    with pytest.raises(ValidationError):
        AppConfig.model_validate(config_dict)


def test_invalid_severity_band_values_raise_validation_error() -> None:
    config_dict = deepcopy(load_config_dict())
    config_dict["rules"]["rules"]["severity_bands"]["low"]["max_score"] = 101

    with pytest.raises(ValidationError):
        AppConfig.model_validate(config_dict)


def test_invalid_isolation_forest_contamination_raises_validation_error() -> None:
    config_dict = deepcopy(load_config_dict())
    config_dict["model"]["isolation_forest"]["contamination"] = 1.0

    with pytest.raises(ValidationError):
        AppConfig.model_validate(config_dict)


def test_invalid_dashboard_page_sizes_raise_validation_error() -> None:
    config_dict = deepcopy(load_config_dict())
    config_dict["dashboard"]["tables"]["default_page_size"] = 501
    config_dict["dashboard"]["tables"]["max_page_size"] = 500

    with pytest.raises(ValidationError):
        AppConfig.model_validate(config_dict)
