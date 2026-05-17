"""Tests for full account feature table calculation and validation."""

import pandas as pd
import pytest

from graph_aml.features import (
    ACCOUNT_FEATURE_COLUMNS,
    calculate_account_features,
    validate_account_features,
)
from graph_aml.features.exceptions import AccountFeatureError


def _accounts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"account_id": "ACC_A", "customer_id": "CUST_A"},
            {"account_id": "ACC_B", "customer_id": "CUST_B"},
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
                "transaction_timestamp": "2025-01-01T10:00:00Z",
                "amount": 10.0,
            },
            {
                "transaction_id": "TXN_002",
                "sender_account_id": "ACC_B",
                "receiver_account_id": "ACC_A",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-03T10:00:00Z",
                "amount": 20.0,
            },
        ]
    )


def test_calculate_account_features_returns_non_empty_dataframe_for_valid_inputs() -> None:
    features = calculate_account_features(_accounts(), _transactions())

    assert not features.empty


def test_output_columns_equal_account_feature_columns() -> None:
    features = calculate_account_features(_accounts(), _transactions())

    assert tuple(features.columns) == ACCOUNT_FEATURE_COLUMNS


def test_feature_dates_cover_expected_date_range() -> None:
    features = calculate_account_features(_accounts(), _transactions())

    assert [str(value.date()) for value in features["feature_date"].drop_duplicates()] == [
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
    ]


def test_account_date_version_combination_is_unique() -> None:
    features = calculate_account_features(_accounts(), _transactions())

    assert not features.duplicated(["account_id", "feature_date", "feature_version"]).any()


def test_empty_valid_transaction_input_returns_empty_feature_dataframe() -> None:
    transactions = _transactions().assign(amount=0)

    features = calculate_account_features(_accounts(), transactions)

    assert features.empty
    assert tuple(features.columns) == ACCOUNT_FEATURE_COLUMNS


def test_inputs_are_not_mutated() -> None:
    accounts = _accounts()
    transactions = _transactions()
    accounts_before = accounts.copy(deep=True)
    transactions_before = transactions.copy(deep=True)

    calculate_account_features(accounts, transactions)

    pd.testing.assert_frame_equal(accounts, accounts_before)
    pd.testing.assert_frame_equal(transactions, transactions_before)


def test_validate_account_features_passes_valid_features() -> None:
    validate_account_features(calculate_account_features(_accounts(), _transactions()))


def test_validate_account_features_fails_on_missing_required_columns() -> None:
    features = calculate_account_features(_accounts(), _transactions()).drop(columns=["account_id"])

    with pytest.raises(AccountFeatureError):
        validate_account_features(features)


def test_validate_account_features_fails_on_negative_counts() -> None:
    features = calculate_account_features(_accounts(), _transactions())
    features.loc[0, "txn_count_7d"] = -1

    with pytest.raises(AccountFeatureError):
        validate_account_features(features)


def test_validate_account_features_fails_on_duplicate_account_date_version_rows() -> None:
    features = calculate_account_features(_accounts(), _transactions())
    duplicate = pd.concat([features, features.iloc[[0]]], ignore_index=True)

    with pytest.raises(AccountFeatureError):
        validate_account_features(duplicate)
