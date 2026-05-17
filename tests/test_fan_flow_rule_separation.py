"""Cross-rule separation tests for fan-in and fan-out."""

from graph_aml.rules import FanInRuleConfig, FanOutRuleConfig, run_fan_in_rule, run_fan_out_rule
from tests.fixtures.fan_flow_fixtures import (
    build_cross_rule_non_trigger_transactions_fixture,
    build_fan_flow_accounts_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
    build_joint_fan_in_and_fan_out_transactions_fixture,
)


def _fan_in_config() -> FanInRuleConfig:
    return FanInRuleConfig(min_unique_senders=4)


def _fan_out_config() -> FanOutRuleConfig:
    return FanOutRuleConfig(min_unique_recipients=4)


def test_fan_in_only_fixture_produces_fan_in_alerts() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    )

    assert len(alerts) == 1


def test_fan_in_only_fixture_does_not_produce_fan_out_alerts() -> None:
    alerts = run_fan_out_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )

    assert alerts == ()


def test_fan_out_only_fixture_produces_fan_out_alerts() -> None:
    alerts = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )

    assert len(alerts) == 1


def test_fan_out_only_fixture_does_not_produce_fan_in_alerts() -> None:
    alerts = run_fan_in_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    )

    assert alerts == ()


def test_cross_rule_benign_fixture_produces_no_fan_in_alerts() -> None:
    alerts = run_fan_in_rule(
        build_cross_rule_non_trigger_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    )

    assert alerts == ()


def test_cross_rule_benign_fixture_produces_no_fan_out_alerts() -> None:
    alerts = run_fan_out_rule(
        build_cross_rule_non_trigger_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )

    assert alerts == ()


def test_internal_receipts_are_receiver_side_concentration() -> None:
    alert = run_fan_in_rule(
        build_fan_in_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_in_config(),
    )[0]

    assert alert.account_id == "ACC_COLLECT_001"


def test_outbound_dispersion_is_sender_side_dispersion() -> None:
    alert = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(),
        build_fan_flow_accounts_fixture(),
        _fan_out_config(),
    )[0]

    assert alert.account_id == "ACC_DISPERSE_001"


def test_rule_outputs_remain_independent_on_same_fixture() -> None:
    frame = build_joint_fan_in_and_fan_out_transactions_fixture()
    accounts = build_fan_flow_accounts_fixture()

    fan_in_alert = run_fan_in_rule(frame, accounts, _fan_in_config())[0]
    fan_out_alert = run_fan_out_rule(frame, accounts, _fan_out_config())[0]

    assert fan_in_alert.rule_name == "Fan-in"
    assert fan_out_alert.rule_name == "Fan-out"
    assert fan_in_alert.account_id != fan_out_alert.account_id
