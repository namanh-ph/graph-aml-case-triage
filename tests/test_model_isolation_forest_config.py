"""Tests for Isolation Forest model configuration."""

from pathlib import Path

import pytest

from graph_aml.models import (
    IsolationForestModelConfig,
    ModelConfigurationError,
    isolation_forest_config_from_mapping,
    load_isolation_forest_config,
)


def test_default_isolation_forest_config_is_valid() -> None:
    assert IsolationForestModelConfig().model_name == "account_isolation_forest"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model_name": ""},
        {"model_version": ""},
        {"n_estimators": 0},
        {"contamination": 0},
        {"contamination": 0.7},
        {"max_samples": 0},
        {"max_samples": 1.5},
        {"max_features": 0},
        {"max_features": 1.5},
        {"score_percentile_medium": 95, "score_percentile_high": 80},
        {
            "use_graph_features": False,
            "use_behavioural_features": False,
            "use_jurisdiction_features": False,
        },
        {"imputation_strategy": "mode"},
        {"scaling_strategy": "minmax"},
    ],
)
def test_invalid_config_values_raise(kwargs: dict[str, object]) -> None:
    with pytest.raises(ModelConfigurationError):
        IsolationForestModelConfig(**kwargs)


def test_config_can_be_built_from_mapping() -> None:
    config = isolation_forest_config_from_mapping(
        {"model_version": "v2", "n_estimators": 10, "mlflow_enabled": False}
    )
    assert config.model_version == "v2"
    assert config.n_estimators == 10
    assert not config.mlflow_enabled


def test_config_can_be_loaded_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "model.yaml"
    path.write_text(
        """
isolation_forest:
  model_name: local_iforest
  model_version: v1
  n_estimators: 25
  min_training_rows: 5
""",
        encoding="utf-8",
    )
    config = load_isolation_forest_config(path)
    assert config.model_name == "local_iforest"
    assert config.n_estimators == 25


def test_config_loading_does_not_connect_to_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("database connection attempted")

    monkeypatch.setattr("sqlalchemy.create_engine", fail, raising=False)
    assert isinstance(
        load_isolation_forest_config("missing-model.yaml"),
        IsolationForestModelConfig,
    )
