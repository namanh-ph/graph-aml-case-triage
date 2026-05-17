"""Configuration for analyst feedback labels."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from graph_aml.labels.exceptions import LabelConfigurationError


@dataclass(frozen=True)
class LabelQualityConfig:
    require_closure_reason: bool = True
    require_comment_for_closure: bool = True
    min_case_labels: int = 1
    min_positive_labels: int = 0
    min_negative_labels: int = 0
    allow_single_class_dataset: bool = True


@dataclass(frozen=True)
class LabelPropagationConfig:
    build_case_labels: bool = True
    build_account_labels: bool = True
    account_label_strategy: str = "max_case_label"
    include_related_accounts: bool = True
    include_primary_account: bool = True


@dataclass(frozen=True)
class LabelLeakageControlConfig:
    enforce_label_timestamp_after_case_created: bool = True
    enforce_feature_timestamp_before_label: bool = True
    label_timestamp_column: str = "action_timestamp"


@dataclass(frozen=True)
class AnalystLabelConfig:
    label_version: str = "analyst_feedback_v1"
    dataset_version: str = "supervised_readiness_v1"
    decision_label_mapping: dict[str, int] = field(
        default_factory=lambda: {
            "Closed suspicious": 1,
            "Closed false positive": 0,
        }
    )
    eligible_terminal_statuses: tuple[str, ...] = (
        "Closed suspicious",
        "Closed false positive",
    )
    excluded_statuses: tuple[str, ...] = (
        "New",
        "In review",
        "Escalated",
        "Information requested",
        "Archived",
    )
    label_quality: LabelQualityConfig = field(default_factory=LabelQualityConfig)
    propagation: LabelPropagationConfig = field(default_factory=LabelPropagationConfig)
    leakage_controls: LabelLeakageControlConfig = field(default_factory=LabelLeakageControlConfig)
    artefact_output_dir: str = "reports/model_validation"


def _as_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise LabelConfigurationError(f"{field_name} must be a list")
    values = tuple(str(item).strip() for item in value)
    if any(not item for item in values):
        raise LabelConfigurationError(f"{field_name} values must be non-empty")
    return values


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise LabelConfigurationError(f"{field_name} must be boolean")
    return value


def _require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LabelConfigurationError(f"{field_name} must be an integer")
    return int(value)


def _unique(values: tuple[str, ...], field_name: str) -> None:
    lowered = [value.lower() for value in values]
    if len(lowered) != len(set(lowered)):
        raise LabelConfigurationError(f"{field_name} values must be unique")


def validate_analyst_label_config(config: AnalystLabelConfig) -> None:
    """Validate analyst label configuration without connecting to services."""

    if not config.label_version.strip():
        raise LabelConfigurationError("label_version must be non-empty")
    if not config.dataset_version.strip():
        raise LabelConfigurationError("dataset_version must be non-empty")
    if not config.decision_label_mapping:
        raise LabelConfigurationError("decision_label_mapping must be non-empty")
    for status, label in config.decision_label_mapping.items():
        if not str(status).strip() or label not in {0, 1}:
            raise LabelConfigurationError("decision mapping labels must be 0 or 1")
    if not config.eligible_terminal_statuses:
        raise LabelConfigurationError("eligible_terminal_statuses must be non-empty")
    for status in config.eligible_terminal_statuses:
        if status not in config.decision_label_mapping:
            raise LabelConfigurationError("eligible terminal statuses must be in mapping")
    _unique(config.excluded_statuses, "excluded_statuses")
    for field_name in (
        "require_closure_reason",
        "require_comment_for_closure",
        "allow_single_class_dataset",
    ):
        _require_bool(getattr(config.label_quality, field_name), f"label_quality.{field_name}")
    for field_name in ("min_case_labels", "min_positive_labels", "min_negative_labels"):
        value = _require_int(
            getattr(config.label_quality, field_name),
            f"label_quality.{field_name}",
        )
        if value < 0:
            raise LabelConfigurationError("minimum label thresholds must be non-negative")
    for field_name in (
        "build_case_labels",
        "build_account_labels",
        "include_related_accounts",
        "include_primary_account",
    ):
        _require_bool(getattr(config.propagation, field_name), f"propagation.{field_name}")
    if not (config.propagation.build_case_labels or config.propagation.build_account_labels):
        raise LabelConfigurationError("at least one label output must be enabled")
    if config.propagation.account_label_strategy not in {
        "max_case_label",
        "latest_case_label",
        "any_suspicious",
    }:
        raise LabelConfigurationError("invalid account_label_strategy")
    for field_name in (
        "enforce_label_timestamp_after_case_created",
        "enforce_feature_timestamp_before_label",
    ):
        _require_bool(
            getattr(config.leakage_controls, field_name),
            f"leakage_controls.{field_name}",
        )
    if not config.leakage_controls.label_timestamp_column.strip():
        raise LabelConfigurationError("label timestamp column must be non-empty")
    if not config.artefact_output_dir.strip():
        raise LabelConfigurationError("artefact_output_dir must be non-empty")


def analyst_label_config_from_mapping(payload: dict[str, object] | None) -> AnalystLabelConfig:
    """Build analyst label configuration from a YAML mapping."""

    if payload is None:
        config = AnalystLabelConfig()
        validate_analyst_label_config(config)
        return config
    section = payload.get("analyst_labels", payload) if isinstance(payload, dict) else payload
    if not isinstance(section, dict):
        raise LabelConfigurationError("analyst label config must be a mapping")
    defaults = AnalystLabelConfig()
    quality_payload = section.get("label_quality", {})
    propagation_payload = section.get("propagation", {})
    leakage_payload = section.get("leakage_controls", {})
    if not isinstance(quality_payload, dict | type(None)):
        raise LabelConfigurationError("label_quality must be a mapping")
    if not isinstance(propagation_payload, dict | type(None)):
        raise LabelConfigurationError("propagation must be a mapping")
    if not isinstance(leakage_payload, dict | type(None)):
        raise LabelConfigurationError("leakage_controls must be a mapping")
    quality_payload = quality_payload or {}
    propagation_payload = propagation_payload or {}
    leakage_payload = leakage_payload or {}
    mapping_payload = section.get("decision_label_mapping", defaults.decision_label_mapping)
    if not isinstance(mapping_payload, dict):
        raise LabelConfigurationError("decision_label_mapping must be a mapping")
    config = AnalystLabelConfig(
        label_version=str(section.get("label_version", defaults.label_version)),
        dataset_version=str(section.get("dataset_version", defaults.dataset_version)),
        decision_label_mapping={str(key): int(value) for key, value in mapping_payload.items()},
        eligible_terminal_statuses=_as_tuple(
            section.get("eligible_terminal_statuses", defaults.eligible_terminal_statuses),
            "eligible_terminal_statuses",
        ),
        excluded_statuses=_as_tuple(
            section.get("excluded_statuses", defaults.excluded_statuses),
            "excluded_statuses",
        ),
        label_quality=LabelQualityConfig(
            require_closure_reason=_require_bool(
                quality_payload.get(
                    "require_closure_reason",
                    defaults.label_quality.require_closure_reason,
                ),
                "label_quality.require_closure_reason",
            ),
            require_comment_for_closure=_require_bool(
                quality_payload.get(
                    "require_comment_for_closure",
                    defaults.label_quality.require_comment_for_closure,
                ),
                "label_quality.require_comment_for_closure",
            ),
            min_case_labels=_require_int(
                quality_payload.get("min_case_labels", defaults.label_quality.min_case_labels),
                "label_quality.min_case_labels",
            ),
            min_positive_labels=_require_int(
                quality_payload.get(
                    "min_positive_labels",
                    defaults.label_quality.min_positive_labels,
                ),
                "label_quality.min_positive_labels",
            ),
            min_negative_labels=_require_int(
                quality_payload.get(
                    "min_negative_labels",
                    defaults.label_quality.min_negative_labels,
                ),
                "label_quality.min_negative_labels",
            ),
            allow_single_class_dataset=_require_bool(
                quality_payload.get(
                    "allow_single_class_dataset",
                    defaults.label_quality.allow_single_class_dataset,
                ),
                "label_quality.allow_single_class_dataset",
            ),
        ),
        propagation=LabelPropagationConfig(
            build_case_labels=_require_bool(
                propagation_payload.get(
                    "build_case_labels",
                    defaults.propagation.build_case_labels,
                ),
                "propagation.build_case_labels",
            ),
            build_account_labels=_require_bool(
                propagation_payload.get(
                    "build_account_labels",
                    defaults.propagation.build_account_labels,
                ),
                "propagation.build_account_labels",
            ),
            account_label_strategy=str(
                propagation_payload.get(
                    "account_label_strategy",
                    defaults.propagation.account_label_strategy,
                )
            ),
            include_related_accounts=_require_bool(
                propagation_payload.get(
                    "include_related_accounts",
                    defaults.propagation.include_related_accounts,
                ),
                "propagation.include_related_accounts",
            ),
            include_primary_account=_require_bool(
                propagation_payload.get(
                    "include_primary_account",
                    defaults.propagation.include_primary_account,
                ),
                "propagation.include_primary_account",
            ),
        ),
        leakage_controls=LabelLeakageControlConfig(
            enforce_label_timestamp_after_case_created=_require_bool(
                leakage_payload.get(
                    "enforce_label_timestamp_after_case_created",
                    defaults.leakage_controls.enforce_label_timestamp_after_case_created,
                ),
                "leakage_controls.enforce_label_timestamp_after_case_created",
            ),
            enforce_feature_timestamp_before_label=_require_bool(
                leakage_payload.get(
                    "enforce_feature_timestamp_before_label",
                    defaults.leakage_controls.enforce_feature_timestamp_before_label,
                ),
                "leakage_controls.enforce_feature_timestamp_before_label",
            ),
            label_timestamp_column=str(
                leakage_payload.get(
                    "label_timestamp_column",
                    defaults.leakage_controls.label_timestamp_column,
                )
            ),
        ),
        artefact_output_dir=str(section.get("artefact_output_dir", defaults.artefact_output_dir)),
    )
    validate_analyst_label_config(config)
    return config


def load_analyst_label_config(
    config_path: Path | str = "config/scoring.yaml",
) -> AnalystLabelConfig:
    """Load analyst label config from scoring YAML."""

    try:
        payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise LabelConfigurationError(f"failed to load label config: {exc}") from exc
    return analyst_label_config_from_mapping(payload)
