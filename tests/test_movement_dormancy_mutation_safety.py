"""Mutation-safety tests for movement and dormancy rule paths."""

import pandas as pd

from graph_aml.rules import (
    build_account_activity_history,
    build_dormant_reactivation_alerts,
    build_rapid_movement_alerts,
    detect_dormant_reactivation_windows,
    detect_rapid_movement_windows,
    filter_dormant_reactivation_outbound_candidates,
    filter_rapid_movement_inbound_transactions,
    filter_rapid_movement_outbound_transactions,
    prepare_dormant_reactivation_transactions,
    prepare_rapid_movement_transactions,
    run_dormant_reactivation_rule,
    run_rapid_movement_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_dormant_reactivation_only_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_prepare_rapid_movement_transactions_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_rapid_movement_only_transactions_fixture(),
        prepare_rapid_movement_transactions,
    )


def test_filter_rapid_inbound_transactions_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_rapid_movement_only_transactions_fixture(),
        filter_rapid_movement_inbound_transactions,
    )


def test_filter_rapid_outbound_transactions_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_rapid_movement_only_transactions_fixture(),
        filter_rapid_movement_outbound_transactions,
    )


def test_detect_rapid_movement_windows_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_rapid_movement_only_transactions_fixture(),
        detect_rapid_movement_windows,
    )


def test_build_rapid_alerts_does_not_mutate_detections_or_accounts() -> None:
    detections = detect_rapid_movement_windows(build_rapid_movement_only_transactions_fixture())
    accounts = build_movement_dormancy_accounts_fixture()
    original_detections = detections.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    build_rapid_movement_alerts(detections, accounts)

    pd.testing.assert_frame_equal(detections, original_detections)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_rapid_movement_rule_does_not_mutate_inputs() -> None:
    transactions = build_rapid_movement_only_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_rapid_movement_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_prepare_dormant_reactivation_transactions_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_dormant_reactivation_only_transactions_fixture(),
        prepare_dormant_reactivation_transactions,
    )


def test_filter_dormant_outbound_candidates_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_dormant_reactivation_only_transactions_fixture(),
        filter_dormant_reactivation_outbound_candidates,
    )


def test_build_account_activity_history_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_dormant_reactivation_only_transactions_fixture(),
        build_account_activity_history,
    )


def test_detect_dormant_reactivation_windows_does_not_mutate_input() -> None:
    _assert_transactions_not_mutated(
        build_dormant_reactivation_only_transactions_fixture(),
        detect_dormant_reactivation_windows,
    )


def test_build_dormant_alerts_does_not_mutate_detections_or_accounts() -> None:
    detections = detect_dormant_reactivation_windows(
        build_dormant_reactivation_only_transactions_fixture()
    )
    accounts = build_movement_dormancy_accounts_fixture()
    original_detections = detections.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    build_dormant_reactivation_alerts(detections, accounts)

    pd.testing.assert_frame_equal(detections, original_detections)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_dormant_reactivation_rule_does_not_mutate_inputs() -> None:
    transactions = build_dormant_reactivation_only_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_dormant_reactivation_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_fixture_helpers_return_independent_dataframes() -> None:
    first = build_rapid_movement_only_transactions_fixture()
    second = build_rapid_movement_only_transactions_fixture()
    first.loc[0, "amount"] = 1

    assert second.loc[0, "amount"] != 1


def _assert_transactions_not_mutated(frame: pd.DataFrame, function) -> None:
    original = frame.copy(deep=True)

    function(frame)

    pd.testing.assert_frame_equal(frame, original)
