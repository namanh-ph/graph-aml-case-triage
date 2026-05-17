"""Fixture-based non-trigger tests for the structuring rule."""

import pandas as pd

from graph_aml.rules import run_structuring_rule
from tests.fixtures.structuring_fixtures import (
    TRANSACTION_COLUMNS,
    build_structuring_invalid_transactions_fixture,
    build_structuring_non_trigger_transactions_fixture,
    build_structuring_trigger_transactions_fixture,
)


def test_one_fewer_than_minimum_count_produces_no_alert(
    structuring_accounts_fixture,
) -> None:
    transactions = build_structuring_trigger_transactions_fixture(count=7)

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_transactions_above_reporting_threshold_produce_no_alert(
    structuring_accounts_fixture,
) -> None:
    transactions = build_structuring_trigger_transactions_fixture(amount=10000.01)

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_transactions_equal_to_reporting_threshold_produce_no_alert(
    structuring_accounts_fixture,
) -> None:
    transactions = build_structuring_trigger_transactions_fixture(amount=10000.0)

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_transactions_below_margin_produce_no_alert(structuring_accounts_fixture) -> None:
    transactions = build_structuring_trigger_transactions_fixture(amount=8999.99)

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_unsupported_transaction_types_produce_no_alert(structuring_accounts_fixture) -> None:
    transactions = build_structuring_trigger_transactions_fixture()
    transactions["transaction_type"] = "card"

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_transactions_outside_rolling_window_produce_no_alert(
    structuring_accounts_fixture,
) -> None:
    transactions = build_structuring_trigger_transactions_fixture()
    start = pd.Timestamp("2025-01-10 09:00:00", tz="UTC")
    transactions["transaction_timestamp"] = [
        start + pd.Timedelta(hours=index * 25) for index in range(len(transactions))
    ]

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_inbound_transactions_do_not_alert_for_receiving_account(
    structuring_accounts_fixture,
) -> None:
    transactions = build_structuring_trigger_transactions_fixture(account_id="ACC_BENIGN_001")
    transactions["receiver_account_id"] = "ACC_STRUCT_001"

    alerts = run_structuring_rule(transactions, structuring_accounts_fixture)

    assert all(alert.account_id != "ACC_STRUCT_001" for alert in alerts)


def test_missing_or_invalid_transactions_are_dropped_before_alerting(
    structuring_accounts_fixture,
) -> None:
    transactions = build_structuring_invalid_transactions_fixture()

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_benign_mixed_activity_produces_no_alert(structuring_accounts_fixture) -> None:
    transactions = build_structuring_non_trigger_transactions_fixture()

    assert run_structuring_rule(transactions, structuring_accounts_fixture) == ()


def test_rule_returns_empty_tuple_for_no_detections(structuring_accounts_fixture) -> None:
    empty = pd.DataFrame(columns=TRANSACTION_COLUMNS)

    assert run_structuring_rule(empty, structuring_accounts_fixture) == ()
