"""Tests for dormant reactivation rule configuration."""

import pytest

from graph_aml.rules import DormantReactivationRuleConfig, RuleConfigurationError


def test_default_dormant_reactivation_rule_config_is_valid() -> None:
    config = DormantReactivationRuleConfig()

    assert config.rule_name == "Dormant reactivation"
    assert config.typology == "dormant_reactivation"


def test_invalid_dormant_days_threshold_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(dormant_days_threshold=0)


def test_invalid_reactivation_window_days_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(reactivation_window_days=0)


def test_invalid_minimum_outbound_amount_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(min_outbound_amount=-1)


def test_invalid_minimum_total_outbound_amount_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(min_total_outbound_amount=-1)


def test_invalid_outbound_transaction_count_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(min_outbound_transaction_count=0)


def test_invalid_severity_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(severity="urgent")


def test_invalid_risk_score_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(base_risk_score=101)
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(high_value_risk_score=-1)


def test_invalid_high_value_multiplier_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(high_value_multiplier=0.99)


def test_empty_outbound_transaction_types_raise() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(outbound_transaction_types=())


def test_disabling_both_outflow_sources_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        DormantReactivationRuleConfig(
            include_counterparty_outflows=False,
            include_internal_account_outflows=False,
        )


def test_constructor_overrides_are_respected() -> None:
    config = DormantReactivationRuleConfig(
        dormant_days_threshold=90,
        reactivation_window_days=3,
        min_outbound_amount=5000,
        min_total_outbound_amount=12000,
        min_outbound_transaction_count=2,
        severity="critical",
        base_risk_score=70,
        high_value_risk_score=95,
        high_value_multiplier=3,
        outbound_transaction_types=("WIRE",),
    )

    assert config.dormant_days_threshold == 90
    assert config.reactivation_window_days == 3
    assert config.min_outbound_amount == 5000
    assert config.min_total_outbound_amount == 12000
    assert config.min_outbound_transaction_count == 2
    assert config.severity == "critical"
    assert config.base_risk_score == 70
    assert config.high_value_risk_score == 95
    assert config.high_value_multiplier == 3
    assert config.outbound_transaction_types == ("wire",)
