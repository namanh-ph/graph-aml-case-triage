"""Tests for account feature calculations."""

import pandas as pd

from graph_aml.features import (
    ACCOUNT_FEATURE_COLUMNS,
    AccountFeatureConfig,
    calculate_features_for_date,
)
from graph_aml.features.account import IN_OUT_RATIO_RECEIVED_ZERO_CAP


def _accounts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"account_id": "ACC_A", "customer_id": "CUST_A", "account_status": "active"},
            {"account_id": "ACC_B", "customer_id": "CUST_B", "account_status": "active"},
            {"account_id": "ACC_C", "customer_id": "CUST_C", "account_status": "dormant"},
        ]
    )


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "TXN_001",
                "sender_account_id": "ACC_A",
                "receiver_account_id": "ACC_B",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-08T10:00:00Z",
                "amount": 100.0,
            },
            {
                "transaction_id": "TXN_002",
                "sender_account_id": "ACC_A",
                "receiver_account_id": None,
                "counterparty_id": "CP_001",
                "transaction_timestamp": "2025-01-07T09:00:00Z",
                "amount": 50.0,
            },
            {
                "transaction_id": "TXN_003",
                "sender_account_id": "ACC_B",
                "receiver_account_id": "ACC_A",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-02T12:00:00Z",
                "amount": 20.0,
            },
            {
                "transaction_id": "TXN_004",
                "sender_account_id": "ACC_A",
                "receiver_account_id": "ACC_B",
                "counterparty_id": None,
                "transaction_timestamp": "2024-12-20T12:00:00Z",
                "amount": 10.0,
            },
        ]
    )


def _features() -> pd.DataFrame:
    return calculate_features_for_date(
        _accounts(),
        _transactions(),
        pd.Timestamp("2025-01-08T00:00:00Z"),
        AccountFeatureConfig(),
    )


def _row(account_id: str) -> pd.Series:
    return _features().set_index("account_id").loc[account_id]


def test_calculate_features_for_date_returns_expected_columns() -> None:
    assert tuple(_features().columns) == ACCOUNT_FEATURE_COLUMNS


def test_txn_count_1d_is_correct() -> None:
    assert _row("ACC_A")["txn_count_1d"] == 2


def test_txn_count_7d_is_correct() -> None:
    assert _row("ACC_A")["txn_count_7d"] == 3


def test_total_sent_7d_is_correct() -> None:
    assert _row("ACC_A")["total_sent_7d"] == 150.0


def test_total_received_7d_is_correct() -> None:
    assert _row("ACC_A")["total_received_7d"] == 20.0


def test_avg_txn_amount_30d_is_correct() -> None:
    assert _row("ACC_A")["avg_txn_amount_30d"] == 45.0


def test_max_txn_amount_30d_is_correct() -> None:
    assert _row("ACC_A")["max_txn_amount_30d"] == 100.0


def test_unique_counterparties_7d_is_correct() -> None:
    assert _row("ACC_A")["unique_counterparties_7d"] == 2


def test_in_out_ratio_7d_is_correct_when_received_value_is_positive() -> None:
    assert _row("ACC_A")["in_out_ratio_7d"] == 7.5


def test_in_out_ratio_7d_is_deterministic_when_received_value_is_zero() -> None:
    transactions = _transactions().iloc[[0]].copy()
    features = calculate_features_for_date(
        _accounts(),
        transactions,
        pd.Timestamp("2025-01-08T00:00:00Z"),
    )
    row = features.set_index("account_id").loc["ACC_A"]

    assert row["in_out_ratio_7d"] == IN_OUT_RATIO_RECEIVED_ZERO_CAP


def test_inactive_accounts_have_zero_features_when_included() -> None:
    row = _row("ACC_C")

    assert row["txn_count_7d"] == 0
    assert row["total_sent_7d"] == 0.0
    assert row["in_out_ratio_7d"] == 0.0


def test_output_is_sorted_deterministically() -> None:
    assert list(_features()["account_id"]) == ["ACC_A", "ACC_B", "ACC_C"]
