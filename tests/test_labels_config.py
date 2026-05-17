from __future__ import annotations

from dataclasses import replace

import pytest

from graph_aml.labels import (
    AnalystLabelConfig,
    LabelConfigurationError,
    LabelPropagationConfig,
    LabelQualityConfig,
    analyst_label_config_from_mapping,
    load_analyst_label_config,
    validate_analyst_label_config,
)


def test_default_analyst_label_config_is_valid() -> None:
    validate_analyst_label_config(AnalystLabelConfig())


def test_invalid_label_version_raises() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(replace(AnalystLabelConfig(), label_version=""))


def test_invalid_dataset_version_raises() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(replace(AnalystLabelConfig(), dataset_version=""))


def test_invalid_decision_mapping_raises() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(
            replace(AnalystLabelConfig(), decision_label_mapping={"Closed suspicious": 2})
        )


def test_eligible_terminal_statuses_missing_from_mapping_raise() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(
            replace(AnalystLabelConfig(), eligible_terminal_statuses=("Missing",))
        )


def test_invalid_quality_thresholds_raise() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(
            replace(
                AnalystLabelConfig(),
                label_quality=replace(LabelQualityConfig(), min_case_labels=-1),
            )
        )


def test_invalid_propagation_strategy_raises() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(
            replace(
                AnalystLabelConfig(),
                propagation=replace(LabelPropagationConfig(), account_label_strategy="bad"),
            )
        )


def test_disabling_both_case_and_account_labels_raises() -> None:
    with pytest.raises(LabelConfigurationError):
        validate_analyst_label_config(
            replace(
                AnalystLabelConfig(),
                propagation=replace(
                    LabelPropagationConfig(),
                    build_case_labels=False,
                    build_account_labels=False,
                ),
            )
        )


def test_config_can_be_built_from_mapping() -> None:
    config = analyst_label_config_from_mapping(
        {"analyst_labels": {"label_version": "v2", "dataset_version": "d2"}}
    )
    assert config.label_version == "v2"


def test_config_can_be_loaded_from_temporary_yaml(tmp_path) -> None:
    path = tmp_path / "scoring.yaml"
    path.write_text(
        "analyst_labels:\n  label_version: v2\n  dataset_version: d2\n",
        encoding="utf-8",
    )
    assert load_analyst_label_config(path).dataset_version == "d2"


def test_config_loading_does_not_connect_to_postgresql(monkeypatch, tmp_path) -> None:
    path = tmp_path / "scoring.yaml"
    path.write_text("analyst_labels:\n  label_version: v2\n", encoding="utf-8")
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: pytest.fail("no db"))
    assert load_analyst_label_config(path).label_version == "v2"
