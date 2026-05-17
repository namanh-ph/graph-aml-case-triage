"""Risk-score tests for fan-in and fan-out."""

import pytest

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    RuleConfigurationError,
    run_fan_in_rule,
    run_fan_out_rule,
)
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
)


def test_fan_in_base_risk_score_is_used_for_standard_detections() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(min_unique_senders=4, high_sender_multiplier=2.0),
    )[0]

    assert alert.risk_score_rule == 80.0


def test_fan_in_high_sender_risk_score_is_used_at_multiplier() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(min_unique_senders=4, high_sender_multiplier=1.0),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_fan_out_base_risk_score_is_used_for_standard_detections() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(min_unique_recipients=4, high_recipient_multiplier=2.0),
    )[0]

    assert alert.risk_score_rule == 80.0


def test_fan_out_high_recipient_risk_score_is_used_at_multiplier() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(min_unique_recipients=4, high_recipient_multiplier=1.0),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_custom_fan_in_base_risk_score_is_respected() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(min_unique_senders=4, base_risk_score=72.5, high_sender_multiplier=2.0),
    )[0]

    assert alert.risk_score_rule == 72.5


def test_custom_fan_in_high_sender_risk_score_is_respected() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanInRuleConfig(
            min_unique_senders=4,
            high_sender_risk_score=96.0,
            high_sender_multiplier=1.0,
        ),
    )[0]

    assert alert.risk_score_rule == 96.0


def test_custom_fan_out_base_risk_score_is_respected() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(
            min_unique_recipients=4,
            base_risk_score=73.5,
            high_recipient_multiplier=2.0,
        ),
    )[0]

    assert alert.risk_score_rule == 73.5


def test_custom_fan_out_high_recipient_risk_score_is_respected() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        FanOutRuleConfig(
            min_unique_recipients=4,
            high_recipient_risk_score=97.0,
            high_recipient_multiplier=1.0,
        ),
    )[0]

    assert alert.risk_score_rule == 97.0


def test_invalid_fan_in_score_configuration_is_rejected() -> None:
    with pytest.raises(RuleConfigurationError):
        FanInRuleConfig(base_risk_score=101)


def test_invalid_fan_out_score_configuration_is_rejected() -> None:
    with pytest.raises(RuleConfigurationError):
        FanOutRuleConfig(high_recipient_risk_score=-1)
