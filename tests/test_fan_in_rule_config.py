"""Tests for fan-in rule configuration."""

import pytest

from graph_aml.rules import FanInRuleConfig, RuleConfigurationError


def test_default_fan_in_rule_config_is_valid() -> None:
    config = FanInRuleConfig()

    assert config.rule_name == "Fan-in"
    assert config.typology == "fan_in"
    assert config.severity == "high"


def test_invalid_min_unique_sender_count_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(min_unique_senders=1)


def test_invalid_window_days_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(window_days=0)


def test_invalid_severity_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(severity="severe")


def test_invalid_risk_score_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(base_risk_score=101)


def test_invalid_high_sender_multiplier_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(high_sender_multiplier=0.9)


def test_invalid_minimum_total_amount_raises_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(min_total_amount=-1)


def test_empty_transaction_types_raise_rule_configuration_error() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(transaction_types=())


def test_constructor_overrides_are_respected() -> None:
    config = FanInRuleConfig(
        min_unique_senders=4,
        window_days=3,
        severity="Medium",
        transaction_types=("WIRE",),
    )

    assert config.min_unique_senders == 4
    assert config.window_days == 3
    assert config.severity == "medium"
    assert config.transaction_types == ("wire",)
