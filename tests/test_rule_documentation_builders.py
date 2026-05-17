"""Tests for AML rule documentation builder functions."""

from graph_aml.rules import (
    build_all_rule_documentation,
    build_circular_flow_rule_documentation,
    build_dormant_reactivation_rule_documentation,
    build_fan_in_rule_documentation,
    build_fan_out_rule_documentation,
    build_rapid_movement_rule_documentation,
    build_structuring_rule_documentation,
)

REQUIRED_ALERT_FIELDS = {
    "alert_id",
    "account_id",
    "customer_id",
    "rule_name",
    "typology",
    "severity",
    "risk_score_rule",
    "reason_code",
    "evidence_ids",
    "detection_window_start",
    "detection_window_end",
}


def test_each_builder_has_expected_rule_identity() -> None:
    expected = {
        "structuring": ("Structuring", "structuring", build_structuring_rule_documentation),
        "fan_in": ("Fan-in", "fan_in", build_fan_in_rule_documentation),
        "fan_out": ("Fan-out", "fan_out", build_fan_out_rule_documentation),
        "rapid_movement": (
            "Rapid movement",
            "rapid_movement",
            build_rapid_movement_rule_documentation,
        ),
        "dormant_reactivation": (
            "Dormant reactivation",
            "dormant_reactivation",
            build_dormant_reactivation_rule_documentation,
        ),
        "circular_flow": ("Circular flow", "circular_flow", build_circular_flow_rule_documentation),
    }

    for rule_key, (rule_name, typology, builder) in expected.items():
        doc = builder()
        assert doc.rule_key == rule_key
        assert doc.rule_name == rule_name
        assert doc.typology == typology


def test_each_rule_has_required_narrative_sections() -> None:
    for doc in build_all_rule_documentation():
        assert doc.business_purpose
        assert doc.detection_logic
        assert doc.thresholds
        assert doc.evidence
        assert doc.limitations
        assert doc.validation_tests
        assert doc.example_alert


def test_example_alert_dictionaries_include_common_alert_fields() -> None:
    for doc in build_all_rule_documentation():
        assert REQUIRED_ALERT_FIELDS.issubset(doc.example_alert)
