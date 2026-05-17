"""Tests for structuring candidate transaction filtering."""

import pandas as pd

from graph_aml.rules import (
    StructuringRuleConfig,
    filter_structuring_candidate_transactions,
)


def _transactions() -> pd.DataFrame:
    rows = [
        ("TXN_KEEP_1", "ACC_1", "ACC_2", None, "2025-01-01T00:00:00Z", 9000, "transfer"),
        ("TXN_KEEP_2", "ACC_1", "ACC_2", None, "2025-01-01T01:00:00Z", 9999, "wire"),
        ("TXN_EQ_THRESHOLD", "ACC_1", "ACC_2", None, "2025-01-01T02:00:00Z", 10000, "wire"),
        ("TXN_ABOVE", "ACC_1", "ACC_2", None, "2025-01-01T03:00:00Z", 10001, "wire"),
        ("TXN_BELOW_MARGIN", "ACC_1", "ACC_2", None, "2025-01-01T04:00:00Z", 8999, "wire"),
        ("TXN_TYPE", "ACC_1", "ACC_2", None, "2025-01-01T05:00:00Z", 9500, "card"),
        ("TXN_COUNTERPARTY", "ACC_1", None, "CP_1", "2025-01-01T06:00:00Z", 9500, "wire"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "transaction_id",
            "sender_account_id",
            "receiver_account_id",
            "counterparty_id",
            "transaction_timestamp",
            "amount",
            "transaction_type",
        ],
    )


def test_candidate_filter_keeps_outbound_transactions_below_threshold() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_KEEP_2" in set(output["transaction_id"])


def test_candidate_filter_keeps_values_at_threshold_times_margin() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_KEEP_1" in set(output["transaction_id"])


def test_candidate_filter_excludes_values_equal_to_reporting_threshold() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_EQ_THRESHOLD" not in set(output["transaction_id"])


def test_candidate_filter_excludes_values_above_reporting_threshold() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_ABOVE" not in set(output["transaction_id"])


def test_candidate_filter_excludes_values_below_margin() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_BELOW_MARGIN" not in set(output["transaction_id"])


def test_candidate_filter_respects_configured_transaction_types() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_TYPE" not in set(output["transaction_id"])


def test_candidate_filter_supports_counterparty_payments_when_enabled() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert "TXN_COUNTERPARTY" in set(output["transaction_id"])


def test_candidate_filter_excludes_counterparty_only_payments_when_disabled() -> None:
    config = StructuringRuleConfig(include_counterparty_payments=False)

    output = filter_structuring_candidate_transactions(_transactions(), config)

    assert "TXN_COUNTERPARTY" not in set(output["transaction_id"])


def test_candidate_filter_adds_canonical_account_id() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert output["account_id"].eq(output["sender_account_id"]).all()


def test_candidate_filter_returns_deterministic_ordering() -> None:
    output = filter_structuring_candidate_transactions(_transactions())

    assert output["transaction_id"].tolist() == sorted(
        output["transaction_id"].tolist(),
        key=lambda txn_id: output.set_index("transaction_id").loc[txn_id, "transaction_timestamp"],
    )


def test_candidate_filter_does_not_mutate_input_dataframes() -> None:
    transactions = _transactions()
    original = transactions.copy(deep=True)

    filter_structuring_candidate_transactions(transactions)

    pd.testing.assert_frame_equal(transactions, original)
