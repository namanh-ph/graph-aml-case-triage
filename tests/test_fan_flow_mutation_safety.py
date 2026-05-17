"""Mutation-safety tests for fan-in and fan-out helpers."""

import pandas as pd

from graph_aml.rules import (
    FanInRuleConfig,
    FanOutRuleConfig,
    build_fan_in_alerts,
    build_fan_out_alerts,
    detect_fan_in_windows,
    detect_fan_out_windows,
    filter_fan_in_candidate_transactions,
    filter_fan_out_candidate_transactions,
    run_fan_in_rule,
    run_fan_out_rule,
)
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
)


def test_filter_fan_in_candidate_transactions_does_not_mutate_input() -> None:
    frame = build_fan_in_only_transactions_fixture()
    original = frame.copy(deep=True)

    filter_fan_in_candidate_transactions(frame, FanInRuleConfig(min_unique_senders=4))

    pd.testing.assert_frame_equal(frame, original)


def test_detect_fan_in_windows_does_not_mutate_input() -> None:
    frame = build_fan_in_only_transactions_fixture()
    original = frame.copy(deep=True)

    detect_fan_in_windows(frame, FanInRuleConfig(min_unique_senders=4))

    pd.testing.assert_frame_equal(frame, original)


def test_build_fan_in_alerts_does_not_mutate_detections_or_accounts() -> None:
    detections = detect_fan_in_windows(
        build_fan_in_only_transactions_fixture(),
        FanInRuleConfig(min_unique_senders=4),
    )
    accounts = build_fan_flow_accounts_fixture()
    original_detections = detections.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    build_fan_in_alerts(detections, accounts, FanInRuleConfig(min_unique_senders=4))

    pd.testing.assert_frame_equal(detections, original_detections)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_fan_in_rule_does_not_mutate_transactions_or_accounts() -> None:
    transactions = build_fan_in_only_transactions_fixture()
    accounts = build_fan_flow_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_fan_in_rule(transactions, accounts, FanInRuleConfig(min_unique_senders=4))

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_filter_fan_out_candidate_transactions_does_not_mutate_input() -> None:
    frame = build_fan_out_only_transactions_fixture()
    original = frame.copy(deep=True)

    filter_fan_out_candidate_transactions(frame, FanOutRuleConfig(min_unique_recipients=4))

    pd.testing.assert_frame_equal(frame, original)


def test_detect_fan_out_windows_does_not_mutate_input() -> None:
    frame = build_fan_out_only_transactions_fixture()
    original = frame.copy(deep=True)

    detect_fan_out_windows(frame, FanOutRuleConfig(min_unique_recipients=4))

    pd.testing.assert_frame_equal(frame, original)


def test_build_fan_out_alerts_does_not_mutate_detections_or_accounts() -> None:
    detections = detect_fan_out_windows(
        build_fan_out_only_transactions_fixture(),
        FanOutRuleConfig(min_unique_recipients=4),
    )
    accounts = build_fan_flow_accounts_fixture()
    original_detections = detections.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    build_fan_out_alerts(detections, accounts, FanOutRuleConfig(min_unique_recipients=4))

    pd.testing.assert_frame_equal(detections, original_detections)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_fan_out_rule_does_not_mutate_transactions_or_accounts() -> None:
    transactions = build_fan_out_only_transactions_fixture()
    accounts = build_fan_flow_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_fan_out_rule(transactions, accounts, FanOutRuleConfig(min_unique_recipients=4))

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_fan_flow_fixture_helpers_return_independent_dataframes() -> None:
    first = build_fan_in_only_transactions_fixture()
    second = build_fan_in_only_transactions_fixture()
    first.loc[0, "amount"] = 999

    assert second.loc[0, "amount"] != 999
