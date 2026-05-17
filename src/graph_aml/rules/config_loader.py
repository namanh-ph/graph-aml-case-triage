"""Configuration loading for the unified AML rule engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from yaml import YAMLError

from graph_aml.rules.circular_flow import (
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
)
from graph_aml.rules.exceptions import (
    RuleConfigurationError,
    RuleEngineConfigurationError,
    RuleRegistryError,
)
from graph_aml.rules.registry import (
    DEFAULT_RULE_ORDER,
    RULE_CIRCULAR_FLOW,
    get_enabled_rule_keys,
    get_rule_definition,
    normalise_rule_key,
    validate_rule_keys,
)


@dataclass(frozen=True)
class RuleEngineRunConfig:
    """Config-driven execution settings for a unified rule-engine run."""

    enabled_rules: tuple[str, ...]
    persist_alerts: bool = False
    write_audit: bool = True
    write_artefacts: bool = True
    output_dir: str = "reports/model_validation"
    limit: int | None = None

    def __post_init__(self) -> None:
        try:
            enabled_rules = validate_rule_keys(tuple(self.enabled_rules))
        except RuleRegistryError as exc:
            raise RuleEngineConfigurationError(str(exc)) from exc
        if self.limit is not None and self.limit < 0:
            raise RuleEngineConfigurationError("limit must be non-negative")
        object.__setattr__(self, "enabled_rules", enabled_rules)
        object.__setattr__(self, "persist_alerts", bool(self.persist_alerts))
        object.__setattr__(self, "write_audit", bool(self.write_audit))
        object.__setattr__(self, "write_artefacts", bool(self.write_artefacts))
        object.__setattr__(self, "output_dir", str(self.output_dir))


def load_rule_engine_run_config(
    config_path: Path | str = "config/rules.yaml",
    requested_rule_keys: tuple[str, ...] | list[str] | None = None,
    disabled_rule_keys: tuple[str, ...] | list[str] | None = None,
    persist_alerts: bool = False,
    write_audit: bool = True,
    write_artefacts: bool = True,
    output_dir: Path | str = "reports/model_validation",
    limit: int | None = None,
) -> RuleEngineRunConfig:
    """Load enabled rule selection and runtime flags for a rule-engine run."""

    if limit is not None and limit < 0:
        raise RuleEngineConfigurationError("limit must be non-negative")
    try:
        rules_payload = _read_rules_payload(config_path)
        yaml_enabled = _enabled_rule_keys_from_payload(rules_payload)
        if requested_rule_keys:
            requested = validate_rule_keys(requested_rule_keys)
            selected = tuple(rule_key for rule_key in requested if rule_key in yaml_enabled)
        else:
            selected = yaml_enabled
        selected = get_enabled_rule_keys(selected, disabled_rule_keys)
        return RuleEngineRunConfig(
            enabled_rules=selected,
            persist_alerts=persist_alerts,
            write_audit=write_audit,
            write_artefacts=write_artefacts,
            output_dir=str(output_dir),
            limit=limit,
        )
    except (RuleEngineConfigurationError, RuleRegistryError) as exc:
        raise RuleEngineConfigurationError(str(exc)) from exc
    except Exception as exc:
        raise RuleEngineConfigurationError(f"Failed to load rule engine run config: {exc}") from exc


def build_rule_config_from_mapping(
    rule_key: str,
    payload: dict[str, object] | None,
) -> object:
    """Build the implementation config object for one rule from YAML payload."""

    try:
        normalised_key = normalise_rule_key(rule_key)
        clean_payload = _without_enabled(payload or {})
        if normalised_key == RULE_CIRCULAR_FLOW:
            return _build_circular_flow_configs(clean_payload)
        definition = get_rule_definition(normalised_key)
        return definition.config_class(**clean_payload)
    except (RuleConfigurationError, RuleRegistryError, TypeError, ValueError) as exc:
        raise RuleEngineConfigurationError(f"Invalid config for rule {rule_key}: {exc}") from exc


def load_individual_rule_configs(
    config_path: Path | str = "config/rules.yaml",
    rule_keys: tuple[str, ...] | list[str] | None = None,
) -> dict[str, object]:
    """Load implementation-specific configs for selected deterministic rules."""

    try:
        rules_payload = _read_rules_payload(config_path)
        selected = (
            validate_rule_keys(rule_keys)
            if rule_keys is not None
            else _enabled_rule_keys_from_payload(rules_payload)
        )
        return {
            rule_key: build_rule_config_from_mapping(
                rule_key,
                _rule_section_payload(rules_payload, rule_key),
            )
            for rule_key in selected
        }
    except (RuleEngineConfigurationError, RuleRegistryError) as exc:
        raise RuleEngineConfigurationError(str(exc)) from exc
    except Exception as exc:
        raise RuleEngineConfigurationError(
            f"Failed to load individual rule configs: {exc}"
        ) from exc


def _read_rules_payload(config_path: Path | str) -> dict[str, object]:
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise RuleEngineConfigurationError(f"Failed to parse YAML file {path}: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise RuleEngineConfigurationError("rules configuration root must be a mapping")
    root = cast(dict[str, object], loaded)
    rules_root = root.get("rules", root)
    if not isinstance(rules_root, dict):
        raise RuleEngineConfigurationError("rules configuration must be a mapping")
    return cast(dict[str, object], rules_root)


def _enabled_rule_keys_from_payload(rules_payload: dict[str, object]) -> tuple[str, ...]:
    if not rules_payload:
        return tuple(DEFAULT_RULE_ORDER)
    if rules_payload.get("enabled") is False:
        return ()
    known_sections = {
        normalise_rule_key(rule_key) for rule_key in rules_payload if _is_known_rule_key(rule_key)
    }
    if not known_sections:
        return tuple(DEFAULT_RULE_ORDER)
    enabled: list[str] = []
    for rule_key in DEFAULT_RULE_ORDER:
        section = _rule_section_payload(rules_payload, rule_key)
        if section is None:
            continue
        if section.get("enabled", True) is not False:
            enabled.append(rule_key)
    return tuple(enabled)


def _rule_section_payload(
    rules_payload: dict[str, object],
    rule_key: str,
) -> dict[str, object] | None:
    normalised = normalise_rule_key(rule_key)
    for key, value in rules_payload.items():
        if not _is_known_rule_key(key):
            continue
        if normalise_rule_key(key) == normalised:
            if not isinstance(value, dict):
                raise RuleEngineConfigurationError(f"rule section for {rule_key} must be a mapping")
            return cast(dict[str, object], value)
    return None


def _is_known_rule_key(rule_key: object) -> bool:
    try:
        normalise_rule_key(str(rule_key))
    except RuleRegistryError:
        return False
    return True


def _without_enabled(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key != "enabled"}


def _build_circular_flow_configs(payload: dict[str, object]) -> dict[str, object]:
    rule_name = str(payload.get("rule_name", "Circular flow"))
    typology = str(payload.get("typology", "circular_flow"))
    detection_payload = payload.get("detection")
    alert_payload = payload.get("alert")
    if detection_payload is None:
        flat_detection = {
            key: payload[key]
            for key in (
                "max_cycle_hops",
                "min_cycle_hops",
                "min_total_amount",
                "max_time_span_hours",
                "transaction_types",
                "include_counterparty_edges",
                "include_self_loops",
                "max_cycles_per_account",
                "max_total_cycles",
            )
            if key in payload
        }
    elif isinstance(detection_payload, dict):
        flat_detection = cast(dict[str, object], detection_payload).copy()
    else:
        raise RuleEngineConfigurationError("circular_flow.detection must be a mapping")
    if alert_payload is None:
        flat_alert: dict[str, object] = {}
    elif isinstance(alert_payload, dict):
        flat_alert = cast(dict[str, object], alert_payload).copy()
    else:
        raise RuleEngineConfigurationError("circular_flow.alert must be a mapping")

    detection_factory = cast(Any, CircularFlowDetectionConfig)
    alert_factory = cast(Any, CircularFlowRuleConfig)
    detection_config = detection_factory(
        rule_name=rule_name,
        typology=typology,
        **flat_detection,
    )
    alert_config = alert_factory(
        rule_name=rule_name,
        typology=typology,
        detection_config=detection_config,
        **flat_alert,
    )
    return {
        "detection_config": detection_config,
        "alert_config": alert_config,
    }
