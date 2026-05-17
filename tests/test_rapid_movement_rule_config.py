"""Tests for rapid movement rule configuration."""

import pytest

from graph_aml.rules import RapidMovementRuleConfig, RuleConfigurationError


def test_default_rapid_movement_rule_config_is_valid() -> None:
    config = RapidMovementRuleConfig()

    assert config.rule_name == "Rapid movement"
    assert config.typology == "rapid_movement"


def test_invalid_outflow_window_hours_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(outflow_window_hours=0)


def test_invalid_minimum_total_received_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(min_total_received=-1)


def test_invalid_outflow_ratio_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(min_outflow_ratio=0)
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(min_outflow_ratio=1.1)


def test_invalid_retained_ratio_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(max_retained_ratio=-0.1)
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(max_retained_ratio=1)


def test_invalid_outgoing_transaction_count_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(min_outgoing_transaction_count=0)


def test_invalid_severity_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(severity="urgent")


def test_invalid_risk_score_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(base_risk_score=101)
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(high_ratio_risk_score=-1)


def test_invalid_high_ratio_threshold_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(min_outflow_ratio=0.9, high_ratio_threshold=0.89)
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(high_ratio_threshold=1.1)


def test_empty_inbound_transaction_types_raise() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(inbound_transaction_types=())


def test_empty_outbound_transaction_types_raise() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(outbound_transaction_types=())


def test_disabling_both_outflow_sources_raises() -> None:
    with pytest.raises(RuleConfigurationError):
        RapidMovementRuleConfig(
            include_counterparty_outflows=False,
            include_internal_account_outflows=False,
        )


def test_constructor_overrides_are_respected() -> None:
    config = RapidMovementRuleConfig(
        outflow_window_hours=24,
        min_total_received=5000,
        min_outflow_ratio=0.8,
        max_retained_ratio=0.2,
        severity="critical",
        inbound_transaction_types=("ACH",),
        outbound_transaction_types=("WIRE",),
    )

    assert config.outflow_window_hours == 24
    assert config.min_total_received == 5000
    assert config.min_outflow_ratio == 0.8
    assert config.max_retained_ratio == 0.2
    assert config.severity == "critical"
    assert config.inbound_transaction_types == ("ach",)
    assert config.outbound_transaction_types == ("wire",)
