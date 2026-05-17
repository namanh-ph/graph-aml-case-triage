"""Tests for AML rule documentation validation and coverage."""

import json
from dataclasses import replace

import pytest

from graph_aml.rules import (
    RuleDocumentationError,
    build_all_rule_documentation,
    check_rule_documentation_coverage,
    get_rule_documentation,
    validate_all_rule_documentation,
    validate_rule_documentation,
)


def test_valid_rule_documentation_passes_validation() -> None:
    validate_rule_documentation(get_rule_documentation("structuring"))


def test_all_generated_rule_documentation_passes_validation() -> None:
    docs = build_all_rule_documentation()

    validate_all_rule_documentation(docs)


def test_missing_business_purpose_fails_validation() -> None:
    doc = replace(get_rule_documentation("structuring"), business_purpose="")

    with pytest.raises(RuleDocumentationError):
        validate_rule_documentation(doc)


def test_missing_threshold_docs_fails_validation() -> None:
    doc = replace(get_rule_documentation("structuring"), thresholds=())

    with pytest.raises(RuleDocumentationError):
        validate_rule_documentation(doc)


def test_missing_evidence_docs_fails_validation() -> None:
    doc = replace(get_rule_documentation("structuring"), evidence=())

    with pytest.raises(RuleDocumentationError):
        validate_rule_documentation(doc)


def test_missing_limitation_docs_fails_validation() -> None:
    doc = replace(get_rule_documentation("structuring"), limitations=())

    with pytest.raises(RuleDocumentationError):
        validate_rule_documentation(doc)


def test_missing_validation_tests_fails_validation() -> None:
    doc = replace(get_rule_documentation("structuring"), validation_tests=())

    with pytest.raises(RuleDocumentationError):
        validate_rule_documentation(doc)


def test_missing_example_alert_fields_fails_validation() -> None:
    alert = dict(get_rule_documentation("structuring").example_alert)
    alert.pop("alert_id")
    doc = replace(get_rule_documentation("structuring"), example_alert=alert)

    with pytest.raises(RuleDocumentationError):
        validate_rule_documentation(doc)


def test_coverage_summary_includes_expected_keys_and_counts() -> None:
    coverage = check_rule_documentation_coverage(build_all_rule_documentation())

    assert {
        "rule_count",
        "rules_documented",
        "missing_rules",
        "missing_sections",
        "threshold_count",
        "evidence_doc_count",
        "limitation_count",
    }.issubset(coverage)
    assert coverage["rule_count"] == 6
    assert coverage["missing_rules"] == []
    json.dumps(coverage, sort_keys=True)
