"""Mutation-safety tests for structuring rule functions and fixtures."""

import pandas as pd

from graph_aml.rules import (
    build_structuring_alerts,
    detect_structuring_windows,
    filter_structuring_candidate_transactions,
    run_structuring_rule,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_trigger_transactions_fixture,
)


def test_filter_structuring_candidates_does_not_mutate_transactions() -> None:
    transactions = build_structuring_trigger_transactions_fixture()
    original = transactions.copy(deep=True)

    filter_structuring_candidate_transactions(transactions)

    pd.testing.assert_frame_equal(transactions, original)


def test_detect_structuring_windows_does_not_mutate_transactions() -> None:
    transactions = build_structuring_trigger_transactions_fixture()
    original = transactions.copy(deep=True)

    detect_structuring_windows(transactions)

    pd.testing.assert_frame_equal(transactions, original)


def test_build_structuring_alerts_does_not_mutate_detections_or_accounts() -> None:
    detections = detect_structuring_windows(build_structuring_trigger_transactions_fixture())
    accounts = build_structuring_accounts_fixture()
    original_detections = detections.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    build_structuring_alerts(detections, accounts)

    pd.testing.assert_frame_equal(detections, original_detections)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_structuring_rule_does_not_mutate_transactions_or_accounts() -> None:
    transactions = build_structuring_trigger_transactions_fixture()
    accounts = build_structuring_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_structuring_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_fixture_helper_functions_return_independent_dataframes() -> None:
    first = build_structuring_trigger_transactions_fixture()
    second = build_structuring_trigger_transactions_fixture()
    first.loc[0, "transaction_id"] = "MUTATED"

    assert second.loc[0, "transaction_id"] == "TXN_STRUCT_TRIGGER_001"
