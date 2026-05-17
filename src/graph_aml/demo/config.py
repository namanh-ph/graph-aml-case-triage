"""Configuration models for controlled local demo orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from graph_aml.demo.exceptions import DemoConfigurationError

DEFAULT_DEMO_COMMANDS: dict[str, str] = {
    "db_reset": "make db-reset",
    "db_health": "python scripts/db.py health",
    "graph_health": "python scripts/graph.py health",
    "generate_data": "make generate-data-scenarios-small",
    "validate_data": "make validate-data-strict",
    "load_data": "make load-data-scenarios",
    "stage_data": "make stage-data",
    "run_rules": "make run-aml-rules-persist",
    "graph_load": "make graph-load",
    "graph_features": "make graph-features-persist",
    "model_scores": "make model-isolation-forest-persist",
    "account_risk_scores": "make account-risk-score-persist",
    "cases_generate": "make cases-generate-persist",
    "case_risk_scores": "make case-risk-score-persist",
    "case_evidence": "make case-evidence-build-persist",
    "dashboard_health": "make dashboard-health",
    "dashboard_summary": "make dashboard-summary",
    "validation_index": "make dashboard-validation-index",
}


@dataclass(frozen=True)
class DemoConfig:
    name: str = "local_full_aml_demo"
    version: str = "demo_v1"
    description: str = "Local end-to-end AML analytics demo using reference data"
    default_dataset_size: str = "small"
    require_explicit_reset: bool = True
    require_services_running: bool = True
    write_readiness_report: bool = True
    write_artefact_index: bool = True
    artefact_output_dir: str = "reports/model_validation"


@dataclass(frozen=True)
class DemoStepConfig:
    full_pipeline: tuple[str, ...] = (
        "db_health",
        "graph_health",
        "generate_data",
        "validate_data",
        "load_data",
        "stage_data",
        "run_rules",
        "graph_load",
        "graph_features",
        "model_scores",
        "account_risk_scores",
        "cases_generate",
        "case_risk_scores",
        "case_evidence",
        "dashboard_health",
        "dashboard_summary",
        "validation_index",
    )


@dataclass(frozen=True)
class DemoCommandConfig:
    commands: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DEMO_COMMANDS))


@dataclass(frozen=True)
class DemoValidationThresholdConfig:
    min_transactions: int = 1
    min_accounts: int = 1
    min_alerts: int = 1
    min_cases: int = 1
    min_case_risk_scores: int = 1
    min_case_evidence_packs: int = 1
    min_audit_events: int = 1
    min_validation_files: int = 1


@dataclass(frozen=True)
class DemoSafetyConfig:
    destructive_steps: tuple[str, ...] = ("db_reset",)
    blocked_without_flag: tuple[str, ...] = (
        "make db-reset",
        "python scripts/db.py reset",
    )
    forbidden_demo_commands: tuple[str, ...] = (
        "rm -rf",
        "DROP DATABASE",
        "docker system prune",
    )


@dataclass(frozen=True)
class DemoOrchestrationConfig:
    demo: DemoConfig = field(default_factory=DemoConfig)
    steps: DemoStepConfig = field(default_factory=DemoStepConfig)
    commands: DemoCommandConfig = field(default_factory=DemoCommandConfig)
    validation_thresholds: DemoValidationThresholdConfig = field(
        default_factory=DemoValidationThresholdConfig
    )
    safety: DemoSafetyConfig = field(default_factory=DemoSafetyConfig)


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise DemoConfigurationError(f"{field_name} must be a list")
    values = tuple(str(item).strip() for item in value)
    if any(not item for item in values):
        raise DemoConfigurationError(f"{field_name} values must be non-empty")
    return values


def _bool_value(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise DemoConfigurationError(f"{field_name} must be a boolean")
    return value


def _int_value(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DemoConfigurationError(f"{field_name} must be an integer")
    return int(value)


def _validate_unique(values: tuple[str, ...], field_name: str) -> None:
    lowered = [value.lower() for value in values]
    if len(lowered) != len(set(lowered)):
        raise DemoConfigurationError(f"{field_name} values must be unique")


def validate_demo_orchestration_config(config: DemoOrchestrationConfig) -> None:
    """Validate demo orchestration configuration without touching services."""

    if not str(config.demo.name).strip():
        raise DemoConfigurationError("demo name must be non-empty")
    if not str(config.demo.version).strip():
        raise DemoConfigurationError("demo version must be non-empty")
    if config.demo.default_dataset_size not in {"small", "medium", "large"}:
        raise DemoConfigurationError("default dataset size must be small, medium, or large")
    for field_name in (
        "require_explicit_reset",
        "require_services_running",
        "write_readiness_report",
        "write_artefact_index",
    ):
        _bool_value(getattr(config.demo, field_name), f"demo.{field_name}")
    if not str(config.demo.artefact_output_dir).strip():
        raise DemoConfigurationError("artefact output directory must be non-empty")

    if not config.steps.full_pipeline:
        raise DemoConfigurationError("full pipeline steps must be non-empty")
    _validate_unique(config.steps.full_pipeline, "full pipeline")

    for step_name in config.steps.full_pipeline:
        command = config.commands.commands.get(step_name)
        if not command or not str(command).strip():
            raise DemoConfigurationError(f"missing command for demo step {step_name}")
    for step_name, command in config.commands.commands.items():
        if not str(step_name).strip() or not str(command).strip():
            raise DemoConfigurationError("demo commands must have non-empty keys and values")

    for field_name, value in vars(config.validation_thresholds).items():
        threshold = _int_value(value, f"validation_thresholds.{field_name}")
        if threshold < 0:
            raise DemoConfigurationError("validation thresholds must be non-negative")

    for field_name in (
        "destructive_steps",
        "blocked_without_flag",
        "forbidden_demo_commands",
    ):
        values = getattr(config.safety, field_name)
        if not values or any(not str(value).strip() for value in values):
            raise DemoConfigurationError(f"safety.{field_name} must contain non-empty strings")


def demo_orchestration_config_from_mapping(
    payload: dict[str, object] | None,
) -> DemoOrchestrationConfig:
    """Build demo orchestration config from a YAML-style mapping."""

    if payload is None:
        config = DemoOrchestrationConfig()
        validate_demo_orchestration_config(config)
        return config
    if not isinstance(payload, dict):
        raise DemoConfigurationError("demo config payload must be a mapping")

    demo_payload = payload.get("demo", {})
    steps_payload = payload.get("steps", {})
    commands_payload = payload.get("commands", {})
    thresholds_payload = payload.get("validation_thresholds", {})
    safety_payload = payload.get("safety", {})

    if not isinstance(demo_payload, dict):
        raise DemoConfigurationError("demo section must be a mapping")
    if not isinstance(steps_payload, dict):
        raise DemoConfigurationError("steps section must be a mapping")
    if not isinstance(commands_payload, dict):
        raise DemoConfigurationError("commands section must be a mapping")
    if not isinstance(thresholds_payload, dict):
        raise DemoConfigurationError("validation_thresholds section must be a mapping")
    if not isinstance(safety_payload, dict):
        raise DemoConfigurationError("safety section must be a mapping")

    default_demo = DemoConfig()
    demo = DemoConfig(
        name=str(demo_payload.get("name", default_demo.name)),
        version=str(demo_payload.get("version", default_demo.version)),
        description=str(demo_payload.get("description", default_demo.description)),
        default_dataset_size=str(
            demo_payload.get("default_dataset_size", default_demo.default_dataset_size)
        ),
        require_explicit_reset=_bool_value(
            demo_payload.get("require_explicit_reset", default_demo.require_explicit_reset),
            "demo.require_explicit_reset",
        ),
        require_services_running=_bool_value(
            demo_payload.get("require_services_running", default_demo.require_services_running),
            "demo.require_services_running",
        ),
        write_readiness_report=_bool_value(
            demo_payload.get("write_readiness_report", default_demo.write_readiness_report),
            "demo.write_readiness_report",
        ),
        write_artefact_index=_bool_value(
            demo_payload.get("write_artefact_index", default_demo.write_artefact_index),
            "demo.write_artefact_index",
        ),
        artefact_output_dir=str(
            demo_payload.get("artefact_output_dir", default_demo.artefact_output_dir)
        ),
    )

    full_pipeline_value = steps_payload.get("full_pipeline", DemoStepConfig().full_pipeline)
    steps = DemoStepConfig(full_pipeline=_string_tuple(full_pipeline_value, "steps.full_pipeline"))

    commands = DemoCommandConfig(
        commands={str(key): str(value) for key, value in commands_payload.items()}
        if commands_payload
        else dict(DEFAULT_DEMO_COMMANDS)
    )

    threshold_defaults = DemoValidationThresholdConfig()
    threshold_values: dict[str, Any] = {}
    for field_name in vars(threshold_defaults):
        threshold_values[field_name] = thresholds_payload.get(
            field_name,
            getattr(threshold_defaults, field_name),
        )
    thresholds = DemoValidationThresholdConfig(
        **{
            field_name: _int_value(value, f"validation_thresholds.{field_name}")
            for field_name, value in threshold_values.items()
        }
    )

    safety_defaults = DemoSafetyConfig()
    safety = DemoSafetyConfig(
        destructive_steps=_string_tuple(
            safety_payload.get("destructive_steps", safety_defaults.destructive_steps),
            "safety.destructive_steps",
        ),
        blocked_without_flag=_string_tuple(
            safety_payload.get("blocked_without_flag", safety_defaults.blocked_without_flag),
            "safety.blocked_without_flag",
        ),
        forbidden_demo_commands=_string_tuple(
            safety_payload.get("forbidden_demo_commands", safety_defaults.forbidden_demo_commands),
            "safety.forbidden_demo_commands",
        ),
    )

    config = DemoOrchestrationConfig(
        demo=demo,
        steps=steps,
        commands=commands,
        validation_thresholds=thresholds,
        safety=safety,
    )
    validate_demo_orchestration_config(config)
    return config


def load_demo_orchestration_config(
    config_path: Path | str = "config/demo.yaml",
) -> DemoOrchestrationConfig:
    """Load demo orchestration configuration from YAML."""

    path = Path(config_path)
    if not path.exists():
        raise DemoConfigurationError(f"demo config not found: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise DemoConfigurationError(f"failed to load demo config: {exc}") from exc
    return demo_orchestration_config_from_mapping(payload)
