"""Tests for deterministic AML rule registry metadata."""

import importlib

import pytest

from graph_aml.rules import (
    DEFAULT_RULE_ORDER,
    RULE_CIRCULAR_FLOW,
    RULE_DORMANT_REACTIVATION,
    RULE_FAN_IN,
    RULE_FAN_OUT,
    RULE_RAPID_MOVEMENT,
    RULE_STRUCTURING,
    RuleRegistryError,
    get_enabled_rule_keys,
    get_rule_definition,
    get_rule_registry,
    normalise_rule_key,
    validate_rule_keys,
)


def test_registry_includes_all_implemented_rules() -> None:
    assert set(get_rule_registry()) == set(DEFAULT_RULE_ORDER)


def test_default_rule_order_is_expected() -> None:
    assert DEFAULT_RULE_ORDER == (
        RULE_STRUCTURING,
        RULE_FAN_IN,
        RULE_FAN_OUT,
        RULE_RAPID_MOVEMENT,
        RULE_DORMANT_REACTIVATION,
        RULE_CIRCULAR_FLOW,
    )


def test_rule_definitions_have_required_metadata() -> None:
    for rule_key, definition in get_rule_registry().items():
        assert definition.rule_key == rule_key
        assert definition.rule_name
        assert definition.typology
        assert definition.config_class
        assert callable(definition.run_in_memory)
        assert callable(definition.run_from_staged)


def test_circular_flow_supports_artefacts() -> None:
    assert get_rule_definition(RULE_CIRCULAR_FLOW).supports_artefacts is True


def test_other_rules_do_not_support_artefacts() -> None:
    for rule_key in DEFAULT_RULE_ORDER:
        if rule_key != RULE_CIRCULAR_FLOW:
            assert get_rule_definition(rule_key).supports_artefacts is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("fan-in", RULE_FAN_IN),
        ("fan-out", RULE_FAN_OUT),
        ("rapid-movement", RULE_RAPID_MOVEMENT),
        ("dormant-reactivation", RULE_DORMANT_REACTIVATION),
        ("circular-flow", RULE_CIRCULAR_FLOW),
    ],
)
def test_normalise_rule_key_handles_hyphenated_aliases(raw: str, expected: str) -> None:
    assert normalise_rule_key(raw) == expected


def test_unknown_rule_keys_raise_registry_error() -> None:
    with pytest.raises(RuleRegistryError):
        normalise_rule_key("unknown")


def test_validate_rule_keys_deduplicates_preserving_order() -> None:
    assert validate_rule_keys(["fan-in", "fan_in", "structuring"]) == (
        RULE_FAN_IN,
        RULE_STRUCTURING,
    )


def test_get_enabled_rule_keys_defaults_to_all_rules() -> None:
    assert get_enabled_rule_keys() == DEFAULT_RULE_ORDER


def test_get_enabled_rule_keys_applies_requested_rules() -> None:
    assert get_enabled_rule_keys(["fan-in", "circular-flow"]) == (
        RULE_FAN_IN,
        RULE_CIRCULAR_FLOW,
    )


def test_get_enabled_rule_keys_applies_disabled_rules() -> None:
    assert get_enabled_rule_keys(disabled_rule_keys=["fan-in", "fan-out"]) == (
        RULE_STRUCTURING,
        RULE_RAPID_MOVEMENT,
        RULE_DORMANT_REACTIVATION,
        RULE_CIRCULAR_FLOW,
    )


def test_registry_import_does_not_attempt_database_connection() -> None:
    module = importlib.import_module("graph_aml.rules.registry")
    assert module.DEFAULT_RULE_ORDER == DEFAULT_RULE_ORDER
