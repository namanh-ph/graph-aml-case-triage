"""Tests for account feature summary utilities."""

import json

import pandas as pd

from graph_aml.features import calculate_account_features, summarise_account_features

EXPECTED_KEYS = {
    "feature_row_count",
    "account_count",
    "feature_version_count",
    "min_feature_date",
    "max_feature_date",
    "mean_txn_count_7d",
    "max_txn_count_7d",
    "mean_total_sent_7d",
    "max_total_sent_7d",
    "mean_total_received_7d",
    "max_total_received_7d",
    "mean_unique_counterparties_7d",
    "max_unique_counterparties_7d",
    "infinite_in_out_ratio_count",
    "zero_activity_row_count",
}


def _features() -> pd.DataFrame:
    accounts = pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])
    transactions = pd.DataFrame(
        [
            {
                "transaction_id": "TXN_001",
                "sender_account_id": "ACC_A",
                "receiver_account_id": "ACC_B",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-01T10:00:00Z",
                "amount": 10.0,
            }
        ]
    )
    return calculate_account_features(accounts, transactions)


def test_summarise_account_features_returns_all_expected_keys() -> None:
    assert set(summarise_account_features(_features())) == EXPECTED_KEYS


def test_summary_row_count_matches_feature_rows() -> None:
    features = _features()

    assert summarise_account_features(features)["feature_row_count"] == len(features)


def test_account_count_is_correct() -> None:
    assert summarise_account_features(_features())["account_count"] == 2


def test_feature_date_range_is_populated() -> None:
    summary = summarise_account_features(_features())

    assert summary["min_feature_date"] == "2025-01-01"
    assert summary["max_feature_date"] == "2025-01-01"


def test_mean_and_max_transaction_counts_are_populated() -> None:
    summary = summarise_account_features(_features())

    assert summary["mean_txn_count_7d"] == 1.0
    assert summary["max_txn_count_7d"] == 1


def test_mean_and_max_sent_and_received_totals_are_populated() -> None:
    summary = summarise_account_features(_features())

    assert summary["mean_total_sent_7d"] == 5.0
    assert summary["max_total_sent_7d"] == 10.0
    assert summary["mean_total_received_7d"] == 5.0
    assert summary["max_total_received_7d"] == 10.0


def test_infinite_in_out_ratio_count_is_correct() -> None:
    features = _features()
    features.loc[0, "in_out_ratio_7d"] = float("inf")

    assert summarise_account_features(features)["infinite_in_out_ratio_count"] == 1


def test_zero_activity_row_count_is_correct() -> None:
    features = _features()
    features.loc[0, "txn_count_7d"] = 0

    assert summarise_account_features(features)["zero_activity_row_count"] == 1


def test_empty_features_are_handled_gracefully() -> None:
    summary = summarise_account_features(pd.DataFrame())

    assert summary["feature_row_count"] == 0
    assert summary["min_feature_date"] is None


def test_summary_is_json_serialisable() -> None:
    json.dumps(summarise_account_features(_features()), sort_keys=True)
