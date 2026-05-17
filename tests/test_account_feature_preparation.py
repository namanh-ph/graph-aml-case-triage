"""Tests for account feature input preparation."""

import pandas as pd
import pytest

from graph_aml.features import build_account_universe, prepare_transactions_for_features
from graph_aml.features.exceptions import FeatureInputError


def _transactions(**overrides: object) -> pd.DataFrame:
    payload = {
        "transaction_id": "txn_001",
        "sender_account_id": "acc_a",
        "receiver_account_id": "acc_b",
        "counterparty_id": None,
        "transaction_timestamp": "2025-01-01T10:00:00Z",
        "amount": "100.50",
    }
    payload.update(overrides)
    return pd.DataFrame([payload])


def _accounts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "account_id": "ACC_A",
                "customer_id": "CUST_A",
                "account_type": "current",
                "account_status": "active",
                "currency": "USD",
                "home_country": "US",
            },
            {
                "account_id": "ACC_B",
                "customer_id": "CUST_B",
                "account_type": "current",
                "account_status": "active",
                "currency": "USD",
                "home_country": "US",
            },
            {
                "account_id": "ACC_C",
                "customer_id": "CUST_C",
                "account_type": "savings",
                "account_status": "dormant",
                "currency": "USD",
                "home_country": "US",
            },
        ]
    )


def test_prepare_transactions_parses_timestamps() -> None:
    output = prepare_transactions_for_features(_transactions())

    assert output.loc[0, "transaction_timestamp"].year == 2025


def test_prepare_transactions_coerces_amounts_to_numeric() -> None:
    output = prepare_transactions_for_features(_transactions())

    assert output.loc[0, "amount"] == 100.50


def test_prepare_transactions_drops_missing_transaction_ids() -> None:
    assert prepare_transactions_for_features(_transactions(transaction_id=None)).empty


def test_prepare_transactions_drops_missing_sender_account_ids() -> None:
    assert prepare_transactions_for_features(_transactions(sender_account_id=None)).empty


def test_prepare_transactions_drops_missing_timestamps() -> None:
    assert prepare_transactions_for_features(_transactions(transaction_timestamp=None)).empty


def test_prepare_transactions_drops_non_positive_amounts() -> None:
    assert prepare_transactions_for_features(_transactions(amount=0)).empty


def test_prepare_transactions_creates_recipient_key_from_receiver_account_id() -> None:
    output = prepare_transactions_for_features(_transactions())

    assert output.loc[0, "recipient_key"] == "ACC_B"


def test_prepare_transactions_creates_recipient_key_from_counterparty_when_receiver_missing() -> (
    None
):
    output = prepare_transactions_for_features(
        _transactions(receiver_account_id=None, counterparty_id="cp_001")
    )

    assert output.loc[0, "recipient_key"] == "CP_001"


def test_prepare_transactions_does_not_mutate_input_dataframes() -> None:
    frame = _transactions()
    before = frame.copy(deep=True)

    prepare_transactions_for_features(frame)

    pd.testing.assert_frame_equal(frame, before)


def test_build_account_universe_includes_all_accounts_when_configured() -> None:
    universe = build_account_universe(
        _accounts(),
        prepare_transactions_for_features(_transactions()),
    )

    assert list(universe["account_id"]) == ["ACC_A", "ACC_B", "ACC_C"]


def test_build_account_universe_includes_active_transaction_accounts_when_configured() -> None:
    universe = build_account_universe(
        _accounts(),
        prepare_transactions_for_features(_transactions()),
        include_all_accounts=False,
    )

    assert list(universe["account_id"]) == ["ACC_A", "ACC_B"]


def test_missing_account_universe_raises_feature_input_error() -> None:
    with pytest.raises(FeatureInputError):
        build_account_universe(pd.DataFrame(), pd.DataFrame(), include_all_accounts=False)
