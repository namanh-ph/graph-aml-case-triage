"""Tests for structuring rule configuration."""

import pytest

from graph_aml.rules import RuleConfigurationError, StructuringRuleConfig


def test_default_structuring_rule_config_is_valid() -> None:
    config = StructuringRuleConfig()

    assert config.rule_name == "Structuring"
    assert config.typology == "structuring"
    assert config.severity == "high"


def test_invalid_reporting_threshold_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(reporting_threshold=0)


def test_invalid_below_threshold_margin_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(below_threshold_margin=1.0)


def test_invalid_minimum_transaction_count_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(min_transaction_count=1)


def test_invalid_window_hours_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(window_hours=0)


def test_invalid_severity_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(severity="severe")


def test_invalid_risk_score_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(base_risk_score=101)


def test_empty_transaction_types_raise_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        StructuringRuleConfig(transaction_types=())


def test_constructor_overrides_are_respected() -> None:
    config = StructuringRuleConfig(
        reporting_threshold=5000,
        min_transaction_count=3,
        window_hours=12,
        severity="Medium",
        transaction_types=("WIRE",),
    )

    assert config.reporting_threshold == 5000
    assert config.min_transaction_count == 3
    assert config.window_hours == 12
    assert config.severity == "medium"
    assert config.transaction_types == ("wire",)
