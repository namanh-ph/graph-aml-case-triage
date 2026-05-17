"""Tests for circular flow alert configuration."""

import pytest

from graph_aml.rules import (
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    RuleConfigurationError,
)


def test_default_circular_flow_rule_config_is_valid() -> None:
    config = CircularFlowRuleConfig()

    assert config.rule_name == "Circular flow"
    assert config.typology == "circular_flow"
    assert config.severity == "high"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("severity", "urgent"),
        ("base_risk_score", -1.0),
        ("high_amount_risk_score", 101.0),
        ("high_amount_threshold", -1.0),
        ("long_cycle_risk_score", 101.0),
        ("long_cycle_hop_threshold", 1),
    ],
)
def test_invalid_circular_flow_rule_config_values_raise(
    field: str,
    value: object,
) -> None:
    with pytest.raises(RuleConfigurationError):
        CircularFlowRuleConfig(**{field: value})


def test_constructor_overrides_are_respected() -> None:
    detection_config = CircularFlowDetectionConfig(max_cycle_hops=3)
    config = CircularFlowRuleConfig(
        rule_name="Custom circular",
        typology="custom_circular",
        severity="critical",
        base_risk_score=70.0,
        high_amount_risk_score=95.0,
        high_amount_threshold=25000.0,
        long_cycle_risk_score=88.0,
        long_cycle_hop_threshold=3,
        detection_config=detection_config,
    )

    assert config.rule_name == "Custom circular"
    assert config.typology == "custom_circular"
    assert config.severity == "critical"
    assert config.base_risk_score == 70.0
    assert config.high_amount_threshold == 25000.0
    assert config.detection_config is detection_config


def test_detection_config_defaults_to_detection_config() -> None:
    config = CircularFlowRuleConfig()

    assert isinstance(config.detection_config, CircularFlowDetectionConfig)


def test_supplied_detection_config_is_preserved() -> None:
    detection_config = CircularFlowDetectionConfig(max_cycle_hops=2)

    config = CircularFlowRuleConfig(detection_config=detection_config)

    assert config.detection_config is detection_config
