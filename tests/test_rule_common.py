"""Tests for shared AML rule utilities."""

import pandas as pd
import pytest

from graph_aml.rules import (
    RuleInputError,
    attach_customer_ids,
    build_rule_reason_code,
    normalise_rule_transactions,
    require_columns,
)


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "txn_1",
                "sender_account_id": "acc_1",
                "receiver_account_id": "acc_2",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-01T00:00:00Z",
                "amount": "100.50",
                "transaction_type": "TRANSFER",
            },
            {
                "transaction_id": None,
                "sender_account_id": "acc_1",
                "transaction_timestamp": "2025-01-01T01:00:00Z",
                "amount": 100,
                "transaction_type": "wire",
            },
            {
                "transaction_id": "txn_3",
                "sender_account_id": None,
                "transaction_timestamp": "2025-01-01T02:00:00Z",
                "amount": 100,
                "transaction_type": "wire",
            },
            {
                "transaction_id": "txn_4",
                "sender_account_id": "acc_1",
                "transaction_timestamp": "2025-01-01T03:00:00Z",
                "amount": 0,
                "transaction_type": "wire",
            },
        ]
    )


def test_require_columns_passes_when_columns_exist() -> None:
    require_columns(pd.DataFrame({"a": [1], "b": [2]}), ("a", "b"), "frame")


def test_require_columns_raises_when_columns_are_missing() -> None:
    with pytest.raises(RuleInputError):
        require_columns(pd.DataFrame({"a": [1]}), ("a", "b"), "frame")


def test_normalise_rule_transactions_parses_timestamps() -> None:
    normalised = normalise_rule_transactions(_transactions())

    assert str(normalised.loc[0, "transaction_timestamp"].tz) == "UTC"


def test_normalise_rule_transactions_coerces_amounts() -> None:
    normalised = normalise_rule_transactions(_transactions())

    assert normalised.loc[0, "amount"] == 100.5


def test_normalise_rule_transactions_drops_missing_transaction_ids() -> None:
    normalised = normalise_rule_transactions(_transactions())

    assert "TXN_2" not in set(normalised["transaction_id"])


def test_normalise_rule_transactions_drops_missing_sender_account_ids() -> None:
    normalised = normalise_rule_transactions(_transactions())

    assert normalised["sender_account_id"].isna().sum() == 0


def test_normalise_rule_transactions_drops_non_positive_amounts() -> None:
    normalised = normalise_rule_transactions(_transactions())

    assert "TXN_4" not in set(normalised["transaction_id"])


def test_normalise_rule_transactions_lowercases_transaction_types() -> None:
    normalised = normalise_rule_transactions(_transactions())

    assert normalised.loc[0, "transaction_type"] == "transfer"


def test_attach_customer_ids_attaches_customer_ids_from_accounts() -> None:
    alerts = pd.DataFrame({"account_id": ["ACC_1"]})
    accounts = pd.DataFrame({"account_id": ["acc_1"], "customer_id": ["CUST_1"]})

    output = attach_customer_ids(alerts, accounts)

    assert output.loc[0, "customer_id"] == "CUST_1"


def test_build_rule_reason_code_returns_deterministic_reason_code_text() -> None:
    assert build_rule_reason_code(8, 10000, 24) == ("8 transfers below threshold within 24 hours")


def test_rule_common_utilities_do_not_mutate_inputs() -> None:
    transactions = _transactions()
    original = transactions.copy(deep=True)

    normalise_rule_transactions(transactions)

    pd.testing.assert_frame_equal(transactions, original)
