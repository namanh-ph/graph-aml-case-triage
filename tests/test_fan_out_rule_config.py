"""Tests for fan-out rule configuration."""

import pytest

from graph_aml.rules import FanOutRuleConfig, RuleConfigurationError


def test_default_fan_out_rule_config_is_valid() -> None:
    config = FanOutRuleConfig()

    assert config.rule_name == "Fan-out"
    assert config.typology == "fan_out"


def test_invalid_minimum_unique_recipient_count_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(min_unique_recipients=1)


def test_invalid_window_days_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(window_days=0)


def test_invalid_severity_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(severity="urgent")


def test_invalid_risk_score_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(base_risk_score=101)

    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(high_recipient_risk_score=-1)


def test_invalid_high_recipient_multiplier_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(high_recipient_multiplier=0.9)


def test_invalid_minimum_total_amount_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(min_total_amount=-1)


def test_empty_transaction_types_raise() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(transaction_types=())


def test_disabling_both_recipient_sources_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(include_counterparties=False, include_internal_accounts=False)


def test_constructor_overrides_are_respected() -> None:
    config = FanOutRuleConfig(
        min_unique_recipients=5,
        window_days=3,
        severity="critical",
        transaction_types=("ACH",),
    )

    assert config.min_unique_recipients == 5
    assert config.window_days == 3
    assert config.severity == "critical"
    assert config.transaction_types == ("ach",)
