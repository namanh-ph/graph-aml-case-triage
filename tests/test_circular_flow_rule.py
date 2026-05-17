"""Tests for end-to-end circular flow rule execution."""

import pandas as pd
import pytest

from graph_aml.rules import (
    CircularFlowDetectionConfig,
    RuleInputError,
    run_circular_flow_rule,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_accounts_fixture,
    build_circular_flow_invalid_transactions_fixture,
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
    build_circular_flow_time_span_boundary_transactions_fixture,
    build_circular_flow_two_hop_transactions_fixture,
)


def test_run_circular_flow_rule_returns_no_alerts_when_no_cycles_exist() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_non_trigger_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert alerts == ()


def test_run_circular_flow_rule_returns_alerts_for_two_hop_cycles() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_two_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_run_circular_flow_rule_returns_alerts_for_three_hop_cycles() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_run_circular_flow_rule_respects_max_cycle_hop_config() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
        detection_config=CircularFlowDetectionConfig(max_cycle_hops=2),
    )

    assert alerts == ()


def test_run_circular_flow_rule_respects_minimum_total_amount_config() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_two_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
        detection_config=CircularFlowDetectionConfig(min_total_amount=10001.0),
    )

    assert alerts == ()


def test_run_circular_flow_rule_respects_max_time_span_config() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_time_span_boundary_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
        detection_config=CircularFlowDetectionConfig(max_time_span_hours=167),
    )

    assert alerts == ()


def test_run_circular_flow_rule_attaches_customer_ids() -> None:
    alerts = run_circular_flow_rule(
        build_circular_flow_two_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert alerts[0].customer_id == "CUST_CF_A"


def test_run_circular_flow_rule_returns_deterministic_alert_ids() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()
    accounts = build_circular_flow_accounts_fixture()

    first = run_circular_flow_rule(transactions, accounts)
    second = run_circular_flow_rule(transactions, accounts)

    assert [alert.alert_id for alert in first] == [alert.alert_id for alert in second]


def test_run_circular_flow_rule_does_not_mutate_inputs() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()
    accounts = build_circular_flow_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_circular_flow_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_circular_flow_rule_raises_for_invalid_inputs() -> None:
    transactions = build_circular_flow_invalid_transactions_fixture().drop(
        columns=["receiver_account_id"]
    )

    with pytest.raises(RuleInputError):
        run_circular_flow_rule(transactions, build_circular_flow_accounts_fixture())
