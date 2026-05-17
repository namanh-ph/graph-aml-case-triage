"""Tests for behavioural account feature calculations."""

import pandas as pd
import pytest

from graph_aml.features import (
    calculate_behavioural_features_for_date,
    calculate_below_threshold_count_24h,
    calculate_counterparty_entropy,
    calculate_dormant_days_before_activity,
    calculate_retained_balance_proxy,
)
from graph_aml.features.exceptions import FeatureInputError

FEATURE_DATE = pd.Timestamp("2025-01-10T00:00:00Z")


def _accounts() -> pd.DataFrame:
    return pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _txn("TXN_PRIOR", "ACC_A", None, "CP_OLD", "2025-01-01T12:00:00Z", 10.0),
            _txn("TXN_SENT_BIG", "ACC_A", "ACC_B", None, "2025-01-09T10:00:00Z", 50000.0),
            _txn("TXN_IN", "ACC_B", "ACC_A", None, "2025-01-10T10:00:00Z", 1000.0),
            _txn("TXN_BT_1", "ACC_A", None, "CP_001", "2025-01-10T11:00:00Z", 9600.0),
            _txn("TXN_BT_2", "ACC_A", None, "CP_002", "2025-01-10T12:00:00Z", 9900.0),
            _txn("TXN_AT", "ACC_A", None, "CP_003", "2025-01-10T13:00:00Z", 10000.0),
            _txn("TXN_LOW", "ACC_A", None, "CP_004", "2025-01-10T14:00:00Z", 9000.0),
        ]
    )


def _txn(
    transaction_id: str,
    sender: str,
    receiver: str | None,
    counterparty: str | None,
    timestamp: str,
    amount: float,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender,
        "receiver_account_id": receiver,
        "counterparty_id": counterparty,
        "transaction_timestamp": timestamp,
        "amount": amount,
    }


def test_retained_balance_proxy_returns_received_minus_sent_value() -> None:
    value = calculate_retained_balance_proxy(_transactions(), "ACC_B", FEATURE_DATE)

    assert value == 49000.0


def test_retained_balance_can_be_negative() -> None:
    value = calculate_retained_balance_proxy(_transactions(), "ACC_A", FEATURE_DATE)

    assert value < 0


def test_below_threshold_count_24h_counts_only_outbound_transactions_below_threshold() -> None:
    count = calculate_below_threshold_count_24h(_transactions(), "ACC_A", FEATURE_DATE)

    assert count == 2


def test_below_threshold_logic_excludes_values_equal_to_or_above_reporting_threshold() -> None:
    transactions = pd.DataFrame(
        [_txn("TXN_AT", "ACC_A", None, "CP_001", "2025-01-10T13:00:00Z", 10000.0)]
    )

    assert calculate_below_threshold_count_24h(transactions, "ACC_A", FEATURE_DATE) == 0


def test_below_threshold_logic_excludes_values_below_margin() -> None:
    transactions = pd.DataFrame(
        [_txn("TXN_LOW", "ACC_A", None, "CP_001", "2025-01-10T13:00:00Z", 9000.0)]
    )

    assert calculate_below_threshold_count_24h(transactions, "ACC_A", FEATURE_DATE) == 0


def test_invalid_threshold_or_margin_values_raise_feature_input_error() -> None:
    with pytest.raises(FeatureInputError):
        calculate_below_threshold_count_24h(_transactions(), "ACC_A", FEATURE_DATE, 0)
    with pytest.raises(FeatureInputError):
        calculate_below_threshold_count_24h(
            _transactions(),
            "ACC_A",
            FEATURE_DATE,
            below_threshold_margin=1.0,
        )


def test_dormant_days_before_activity_returns_expected_inactive_gap() -> None:
    assert calculate_dormant_days_before_activity(_transactions(), "ACC_A", FEATURE_DATE) == 8


def test_dormant_days_returns_none_when_there_is_no_current_activity() -> None:
    assert calculate_dormant_days_before_activity(_transactions(), "ACC_Z", FEATURE_DATE) is None


def test_counterparty_entropy_returns_zero_for_single_counterparty() -> None:
    transactions = pd.DataFrame(
        [
            _txn("TXN_1", "ACC_A", None, "CP_001", "2025-01-10T10:00:00Z", 10.0),
            _txn("TXN_2", "ACC_A", None, "CP_001", "2025-01-10T11:00:00Z", 10.0),
        ]
    )

    assert calculate_counterparty_entropy(transactions, "ACC_A", FEATURE_DATE) == 0.0


def test_counterparty_entropy_increases_when_counterparties_are_more_diverse() -> None:
    single = pd.DataFrame(
        [
            _txn("TXN_1", "ACC_A", None, "CP_001", "2025-01-10T10:00:00Z", 10.0),
            _txn("TXN_2", "ACC_A", None, "CP_001", "2025-01-10T11:00:00Z", 10.0),
        ]
    )
    diverse = pd.DataFrame(
        [
            _txn("TXN_1", "ACC_A", None, "CP_001", "2025-01-10T10:00:00Z", 10.0),
            _txn("TXN_2", "ACC_A", None, "CP_002", "2025-01-10T11:00:00Z", 10.0),
        ]
    )

    assert calculate_counterparty_entropy(diverse, "ACC_A", FEATURE_DATE) > (
        calculate_counterparty_entropy(single, "ACC_A", FEATURE_DATE)
    )


def test_calculate_behavioural_features_for_date_returns_one_row_per_account() -> None:
    features = calculate_behavioural_features_for_date(_accounts(), _transactions(), FEATURE_DATE)

    assert list(features["account_id"]) == ["ACC_A", "ACC_B"]


def test_input_dataframes_are_not_mutated() -> None:
    accounts = _accounts()
    transactions = _transactions()
    accounts_before = accounts.copy(deep=True)
    transactions_before = transactions.copy(deep=True)

    calculate_behavioural_features_for_date(accounts, transactions, FEATURE_DATE)

    pd.testing.assert_frame_equal(accounts, accounts_before)
    pd.testing.assert_frame_equal(transactions, transactions_before)
