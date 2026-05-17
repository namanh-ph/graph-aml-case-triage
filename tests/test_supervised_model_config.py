from __future__ import annotations

import yaml

from graph_aml.models import (
    SupervisedDatasetConfig,
    SupervisedEvaluationConfig,
    SupervisedModelConfig,
    SupervisedModelConfigurationError,
    SupervisedPreprocessingConfig,
    SupervisedSplitConfig,
    load_supervised_model_config,
    supervised_model_config_from_mapping,
    validate_supervised_model_config,
)


def test_default_supervised_model_config_is_valid() -> None:
    validate_supervised_model_config(SupervisedModelConfig())


def test_invalid_model_family_raises() -> None:
    config = SupervisedModelConfig(model_family="bad")
    try:
        validate_supervised_model_config(config)
    except SupervisedModelConfigurationError:
        return
    raise AssertionError("expected configuration error")


def test_invalid_model_name_raises() -> None:
    config = SupervisedModelConfig(model_name="")
    try:
        validate_supervised_model_config(config)
    except SupervisedModelConfigurationError:
        return
    raise AssertionError("expected configuration error")


def test_invalid_dataset_level_raises() -> None:
    config = SupervisedModelConfig(dataset=SupervisedDatasetConfig(level="customer"))
    try:
        validate_supervised_model_config(config)
    except SupervisedModelConfigurationError:
        return
    raise AssertionError("expected configuration error")


def test_invalid_split_config_raises() -> None:
    config = SupervisedModelConfig(split=SupervisedSplitConfig(validation_fraction=0.9))
    try:
        validate_supervised_model_config(config)
    except SupervisedModelConfigurationError:
        return
    raise AssertionError("expected configuration error")


def test_invalid_preprocessing_config_raises() -> None:
    config = SupervisedModelConfig(
        preprocessing=SupervisedPreprocessingConfig(numeric_imputation="mode")
    )
    try:
        validate_supervised_model_config(config)
    except SupervisedModelConfigurationError:
        return
    raise AssertionError("expected configuration error")


def test_invalid_evaluation_config_raises() -> None:
    config = SupervisedModelConfig(
        evaluation=SupervisedEvaluationConfig(top_k_values=(10, 10))
    )
    try:
        validate_supervised_model_config(config)
    except SupervisedModelConfigurationError:
        return
    raise AssertionError("expected configuration error")


def test_config_from_mapping() -> None:
    config = supervised_model_config_from_mapping(
        {"supervised": {"model_family": "random_forest", "dataset": {"level": "account"}}}
    )
    assert config.model_family == "random_forest"
    assert config.dataset.level == "account"


def test_config_loads_from_temporary_yaml(tmp_path) -> None:
    path = tmp_path / "model.yaml"
    path.write_text(
        yaml.safe_dump({"supervised": {"model_version": "v2"}}),
        encoding="utf-8",
    )
    assert load_supervised_model_config(path).model_version == "v2"


def test_config_loading_does_not_connect_to_postgres(monkeypatch, tmp_path) -> None:
    path = tmp_path / "model.yaml"
    path.write_text("supervised: {}\n", encoding="utf-8")
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: None)
    assert load_supervised_model_config(path).model_name
