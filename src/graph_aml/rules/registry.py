"""Registry for deterministic AML rule implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from graph_aml.rules.circular_flow import CircularFlowRuleConfig, run_circular_flow_rule
from graph_aml.rules.dormant_reactivation import (
    DormantReactivationRuleConfig,
    run_dormant_reactivation_rule,
)
from graph_aml.rules.exceptions import RuleRegistryError
from graph_aml.rules.fan_in import FanInRuleConfig, run_fan_in_rule
from graph_aml.rules.fan_out import FanOutRuleConfig, run_fan_out_rule
from graph_aml.rules.rapid_movement import RapidMovementRuleConfig, run_rapid_movement_rule
from graph_aml.rules.staged import (
    run_circular_flow_rule_from_staged,
    run_dormant_reactivation_rule_from_staged,
    run_fan_in_rule_from_staged,
    run_fan_out_rule_from_staged,
    run_rapid_movement_rule_from_staged,
    run_structuring_rule_from_staged,
)
from graph_aml.rules.structuring import StructuringRuleConfig, run_structuring_rule

RULE_STRUCTURING = "structuring"
RULE_FAN_IN = "fan_in"
RULE_FAN_OUT = "fan_out"
RULE_RAPID_MOVEMENT = "rapid_movement"
RULE_DORMANT_REACTIVATION = "dormant_reactivation"
RULE_CIRCULAR_FLOW = "circular_flow"

DEFAULT_RULE_ORDER = (
    RULE_STRUCTURING,
    RULE_FAN_IN,
    RULE_FAN_OUT,
    RULE_RAPID_MOVEMENT,
    RULE_DORMANT_REACTIVATION,
    RULE_CIRCULAR_FLOW,
)

_RULE_ALIASES = {
    "fan-in": RULE_FAN_IN,
    "fan_out": RULE_FAN_OUT,
    "fan-out": RULE_FAN_OUT,
    "rapid-movement": RULE_RAPID_MOVEMENT,
    "dormant-reactivation": RULE_DORMANT_REACTIVATION,
    "circular-flow": RULE_CIRCULAR_FLOW,
}


@dataclass(frozen=True)
class RuleDefinition:
    """Metadata and callable entrypoints for one deterministic AML rule."""

    rule_key: str
    rule_name: str
    typology: str
    config_class: type
    run_in_memory: Callable
    run_from_staged: Callable
    supports_persistence: bool = True
    supports_artefacts: bool = False


def get_rule_registry() -> dict[str, RuleDefinition]:
    """Return all registered deterministic AML rules in canonical order."""

    definitions = (
        RuleDefinition(
            rule_key=RULE_STRUCTURING,
            rule_name="Structuring",
            typology="structuring",
            config_class=StructuringRuleConfig,
            run_in_memory=run_structuring_rule,
            run_from_staged=run_structuring_rule_from_staged,
        ),
        RuleDefinition(
            rule_key=RULE_FAN_IN,
            rule_name="Fan-in",
            typology="fan_in",
            config_class=FanInRuleConfig,
            run_in_memory=run_fan_in_rule,
            run_from_staged=run_fan_in_rule_from_staged,
        ),
        RuleDefinition(
            rule_key=RULE_FAN_OUT,
            rule_name="Fan-out",
            typology="fan_out",
            config_class=FanOutRuleConfig,
            run_in_memory=run_fan_out_rule,
            run_from_staged=run_fan_out_rule_from_staged,
        ),
        RuleDefinition(
            rule_key=RULE_RAPID_MOVEMENT,
            rule_name="Rapid movement",
            typology="rapid_movement",
            config_class=RapidMovementRuleConfig,
            run_in_memory=run_rapid_movement_rule,
            run_from_staged=run_rapid_movement_rule_from_staged,
        ),
        RuleDefinition(
            rule_key=RULE_DORMANT_REACTIVATION,
            rule_name="Dormant reactivation",
            typology="dormant_reactivation",
            config_class=DormantReactivationRuleConfig,
            run_in_memory=run_dormant_reactivation_rule,
            run_from_staged=run_dormant_reactivation_rule_from_staged,
        ),
        RuleDefinition(
            rule_key=RULE_CIRCULAR_FLOW,
            rule_name="Circular flow",
            typology="circular_flow",
            config_class=CircularFlowRuleConfig,
            run_in_memory=run_circular_flow_rule,
            run_from_staged=run_circular_flow_rule_from_staged,
            supports_artefacts=True,
        ),
    )
    return {definition.rule_key: definition for definition in definitions}


def normalise_rule_key(rule_key: str) -> str:
    """Normalise user-facing rule spellings to canonical registry keys."""

    text = str(rule_key).strip().lower().replace(" ", "_")
    if not text:
        raise RuleRegistryError("rule key is required")
    normalised = _RULE_ALIASES.get(text, text)
    if normalised not in DEFAULT_RULE_ORDER:
        raise RuleRegistryError(f"Unknown rule key: {rule_key}")
    return normalised


def get_rule_definition(rule_key: str) -> RuleDefinition:
    """Return a rule definition by canonical or aliased key."""

    normalised = normalise_rule_key(rule_key)
    registry = get_rule_registry()
    try:
        return registry[normalised]
    except KeyError as exc:
        raise RuleRegistryError(f"Rule is not registered: {rule_key}") from exc


def validate_rule_keys(rule_keys: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Validate and deduplicate rule keys while preserving input order."""

    seen: set[str] = set()
    validated: list[str] = []
    for rule_key in rule_keys:
        normalised = normalise_rule_key(rule_key)
        if normalised not in seen:
            validated.append(normalised)
            seen.add(normalised)
    return tuple(validated)


def get_enabled_rule_keys(
    requested_rule_keys: tuple[str, ...] | list[str] | None = None,
    disabled_rule_keys: tuple[str, ...] | list[str] | None = None,
) -> tuple[str, ...]:
    """Resolve selected rule keys after optional inclusions and exclusions."""

    selected = (
        validate_rule_keys(requested_rule_keys)
        if requested_rule_keys
        else tuple(DEFAULT_RULE_ORDER)
    )
    disabled = set(validate_rule_keys(disabled_rule_keys)) if disabled_rule_keys else set()
    return tuple(rule_key for rule_key in selected if rule_key not in disabled)
