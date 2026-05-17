from __future__ import annotations

from dataclasses import replace

import pytest

from graph_aml.demo import (
    DemoConfig,
    DemoConfigurationError,
    DemoOrchestrationConfig,
    DemoSafetyConfig,
    DemoStepConfig,
    DemoValidationThresholdConfig,
    demo_orchestration_config_from_mapping,
    load_demo_orchestration_config,
    validate_demo_orchestration_config,
)


def test_default_demo_config_is_valid() -> None:
    validate_demo_orchestration_config(DemoOrchestrationConfig())


def test_invalid_demo_name_raises() -> None:
    config = replace(DemoOrchestrationConfig(), demo=replace(DemoConfig(), name=" "))
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_invalid_demo_version_raises() -> None:
    config = replace(DemoOrchestrationConfig(), demo=replace(DemoConfig(), version=""))
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_invalid_dataset_size_raises() -> None:
    config = replace(
        DemoOrchestrationConfig(),
        demo=replace(DemoConfig(), default_dataset_size="x"),
    )
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_invalid_boolean_flags_raise() -> None:
    config = replace(
        DemoOrchestrationConfig(),
        demo=replace(DemoConfig(), require_explicit_reset="yes"),  # type: ignore[arg-type]
    )
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_missing_command_for_configured_step_raises() -> None:
    config = replace(
        DemoOrchestrationConfig(),
        steps=DemoStepConfig(full_pipeline=("missing_step",)),
    )
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_duplicate_full_pipeline_steps_raise() -> None:
    config = replace(
        DemoOrchestrationConfig(),
        steps=DemoStepConfig(full_pipeline=("db_health", "db_health")),
    )
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_invalid_threshold_values_raise() -> None:
    config = replace(
        DemoOrchestrationConfig(),
        validation_thresholds=replace(DemoValidationThresholdConfig(), min_alerts=-1),
    )
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_empty_forbidden_command_values_raise() -> None:
    config = replace(
        DemoOrchestrationConfig(),
        safety=replace(DemoSafetyConfig(), forbidden_demo_commands=(" ",)),
    )
    with pytest.raises(DemoConfigurationError):
        validate_demo_orchestration_config(config)


def test_config_can_be_built_from_mapping() -> None:
    config = demo_orchestration_config_from_mapping(
        {
            "demo": {"name": "demo_x", "version": "v1"},
            "steps": {"full_pipeline": ["db_health"]},
            "commands": {"db_health": "python scripts/db.py health"},
        }
    )
    assert config.demo.name == "demo_x"
    assert config.steps.full_pipeline == ("db_health",)


def test_config_can_be_loaded_from_yaml(tmp_path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text(
        """
demo:
  name: local
  version: v1
steps:
  full_pipeline:
    - db_health
commands:
  db_health: "python scripts/db.py health"
""",
        encoding="utf-8",
    )
    assert load_demo_orchestration_config(path).demo.name == "local"


def test_config_loading_does_not_connect_to_services(monkeypatch, tmp_path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text(
        "steps:\n  full_pipeline:\n    - db_health\ncommands:\n  db_health: x\n",
        encoding="utf-8",
    )

    def fail_connect(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("service connection should not occur")

    monkeypatch.setattr("sqlalchemy.create_engine", fail_connect)
    assert load_demo_orchestration_config(path).commands.commands["db_health"] == "x"
