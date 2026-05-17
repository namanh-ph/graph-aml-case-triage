"""Tests for reusable structuring fixture helpers."""

import pandas as pd

from tests.fixtures import structuring_fixtures as fixtures

REQUIRED_ACCOUNT_COLUMNS = {"account_id", "customer_id"}
REQUIRED_TRANSACTION_COLUMNS = {
    "transaction_id",
    "sender_account_id",
    "receiver_account_id",
    "counterparty_id",
    "transaction_timestamp",
    "amount",
    "transaction_type",
}


def test_fixture_helper_module_imports_successfully() -> None:
    assert fixtures.build_structuring_accounts_fixture is not None


def test_account_fixture_contains_required_account_columns() -> None:
    accounts = fixtures.build_structuring_accounts_fixture()

    assert REQUIRED_ACCOUNT_COLUMNS.issubset(accounts.columns)
    assert {"ACC_STRUCT_001", "ACC_STRUCT_002", "ACC_BENIGN_001"}.issubset(
        set(accounts["account_id"])
    )


def test_transaction_fixtures_contain_required_transaction_columns() -> None:
    builders = (
        fixtures.build_structuring_trigger_transactions_fixture,
        fixtures.build_structuring_non_trigger_transactions_fixture,
        fixtures.build_structuring_boundary_transactions_fixture,
        fixtures.build_structuring_multi_account_transactions_fixture,
        fixtures.build_structuring_overlapping_window_transactions_fixture,
        fixtures.build_structuring_counterparty_transactions_fixture,
        fixtures.build_structuring_invalid_transactions_fixture,
    )

    for builder in builders:
        assert REQUIRED_TRANSACTION_COLUMNS.issubset(builder().columns)


def test_trigger_fixture_produces_configured_transaction_count() -> None:
    assert len(fixtures.build_structuring_trigger_transactions_fixture(count=8)) == 8


def test_boundary_fixture_contains_expected_boundary_examples() -> None:
    amounts = set(fixtures.build_structuring_boundary_transactions_fixture()["amount"])

    assert {8999.99, 9000.0, 9999.99, 10000.0, 10000.01}.issubset(amounts)


def test_multi_account_fixture_contains_separable_activity() -> None:
    frame = fixtures.build_structuring_multi_account_transactions_fixture()

    assert {"ACC_STRUCT_001", "ACC_STRUCT_002", "ACC_BENIGN_001"}.issubset(
        set(frame["sender_account_id"])
    )


def test_overlapping_window_fixture_contains_overlapping_candidate_windows() -> None:
    frame = fixtures.build_structuring_overlapping_window_transactions_fixture()

    assert len(frame) == 9
    assert frame["sender_account_id"].nunique() == 1


def test_fixture_helpers_are_deterministic_across_repeated_calls() -> None:
    first = fixtures.build_structuring_trigger_transactions_fixture()
    second = fixtures.build_structuring_trigger_transactions_fixture()

    pd.testing.assert_frame_equal(first, second)
