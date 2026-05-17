"""Tests for AML rule documentation serialisation helpers."""

import json

import pytest

from graph_aml.rules import (
    RuleDocumentationError,
    build_all_rule_documentation,
    get_rule_documentation,
    rule_documentation_collection_to_dicts,
    rule_documentation_from_dict,
    rule_documentation_to_dict,
)


def test_rule_documentation_to_dict_returns_json_serialisable_payload() -> None:
    payload = rule_documentation_to_dict(get_rule_documentation("structuring"))

    json.dumps(payload, sort_keys=True)


def test_nested_documentation_docs_serialise_as_dictionaries() -> None:
    payload = rule_documentation_to_dict(get_rule_documentation("structuring"))

    assert isinstance(payload["thresholds"], list)
    assert isinstance(payload["thresholds"][0], dict)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["evidence"][0], dict)
    assert isinstance(payload["limitations"], list)
    assert isinstance(payload["limitations"][0], dict)


def test_rule_documentation_from_dict_reconstructs_valid_documentation() -> None:
    original = get_rule_documentation("rapid_movement")
    restored = rule_documentation_from_dict(rule_documentation_to_dict(original))

    assert restored.rule_key == original.rule_key
    assert restored.thresholds == original.thresholds
    assert restored.evidence == original.evidence
    assert restored.limitations == original.limitations


def test_collection_serialisation_returns_all_six_rules() -> None:
    payload = rule_documentation_collection_to_dicts(build_all_rule_documentation())

    assert len(payload) == 6
    assert {item["rule_key"] for item in payload} == {
        "structuring",
        "fan_in",
        "fan_out",
        "rapid_movement",
        "dormant_reactivation",
        "circular_flow",
    }


def test_empty_or_invalid_payload_raises_documentation_error() -> None:
    with pytest.raises(RuleDocumentationError):
        rule_documentation_from_dict({})
