"""Tests for AML rule documentation models and registry helpers."""

from dataclasses import FrozenInstanceError

import pytest

from graph_aml.rules import (
    DEFAULT_RULE_ORDER,
    REQUIRED_RULE_DOCUMENTATION_SECTIONS,
    RuleDocumentation,
    RuleEvidenceDoc,
    RuleLimitationDoc,
    RuleRegistryError,
    RuleThresholdDoc,
    build_all_rule_documentation,
    get_rule_documentation,
    get_rule_documentation_registry,
)


def test_rule_threshold_doc_is_immutable() -> None:
    doc = RuleThresholdDoc("name", 1, "description", "rationale", "guidance", "rules.x.name")

    with pytest.raises(FrozenInstanceError):
        doc.name = "other"  # type: ignore[misc]


def test_rule_evidence_doc_is_immutable() -> None:
    doc = RuleEvidenceDoc("transaction_ids", "description", "TXN_001", ("transaction_id",))

    with pytest.raises(FrozenInstanceError):
        doc.example = "TXN_002"  # type: ignore[misc]


def test_rule_limitation_doc_is_immutable() -> None:
    doc = RuleLimitationDoc("limitation", "mitigation")

    with pytest.raises(FrozenInstanceError):
        doc.mitigation = "other"  # type: ignore[misc]


def test_rule_documentation_is_immutable() -> None:
    documentation = get_rule_documentation("structuring")

    with pytest.raises(FrozenInstanceError):
        documentation.rule_name = "Other"  # type: ignore[misc]


def test_required_documentation_sections_include_expected_sections() -> None:
    expected = {
        "business_purpose",
        "detection_logic",
        "input_tables",
        "required_columns",
        "thresholds",
        "alert_fields",
        "reason_code_format",
        "evidence",
        "scoring_logic",
        "example_scenario",
        "example_alert",
        "limitations",
        "validation_tests",
    }

    assert expected.issubset(REQUIRED_RULE_DOCUMENTATION_SECTIONS)


def test_documentation_registry_includes_all_six_rules() -> None:
    registry = get_rule_documentation_registry()

    assert tuple(registry) == DEFAULT_RULE_ORDER
    assert len(registry) == 6
    assert all(isinstance(doc, RuleDocumentation) for doc in registry.values())


def test_documentation_registry_preserves_canonical_rule_order() -> None:
    docs = build_all_rule_documentation()

    assert tuple(doc.rule_key for doc in docs) == DEFAULT_RULE_ORDER


def test_get_rule_documentation_supports_hyphenated_aliases() -> None:
    assert get_rule_documentation("fan-in").rule_key == "fan_in"
    assert get_rule_documentation("rapid-movement").rule_key == "rapid_movement"
    assert get_rule_documentation("circular-flow").rule_key == "circular_flow"


def test_unknown_rule_documentation_key_raises() -> None:
    with pytest.raises(RuleRegistryError):
        get_rule_documentation("unknown-rule")


def test_documentation_objects_do_not_require_database_connection() -> None:
    docs = build_all_rule_documentation()

    assert len(docs) == 6
    assert all(doc.input_tables for doc in docs)
