"""Tests for jurisdiction account feature calculations."""

import pandas as pd

from graph_aml.features import (
    calculate_cross_border_ratio_30d,
    calculate_high_risk_country_exposure,
    calculate_jurisdiction_features_for_date,
)

FEATURE_DATE = pd.Timestamp("2025-01-10T00:00:00Z")


def _accounts() -> pd.DataFrame:
    return pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])


def _countries() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"country_code": "US", "is_high_risk": False, "risk_score": 10.0},
            {"country_code": "PA", "is_high_risk": True, "risk_score": 80.0},
            {"country_code": "VG", "is_high_risk": True, "risk_score": None},
            {"country_code": "GB", "is_high_risk": False, "risk_score": None},
        ]
    )


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _txn("TXN_1", "ACC_A", "ACC_B", "2025-01-10T10:00:00Z", 100.0, "US", "PA", True),
            _txn("TXN_2", "ACC_B", "ACC_A", "2025-01-10T11:00:00Z", 100.0, "GB", "US", True),
            _txn("TXN_3", "ACC_A", "ACC_B", "2025-01-10T12:00:00Z", 100.0, "US", "US", False),
        ]
    )


def _txn(
    transaction_id: str,
    sender: str,
    receiver: str | None,
    timestamp: str,
    amount: float,
    origin: str,
    destination: str,
    cross_border: bool,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender,
        "receiver_account_id": receiver,
        "counterparty_id": None,
        "transaction_timestamp": timestamp,
        "amount": amount,
        "origin_country": origin,
        "destination_country": destination,
        "is_cross_border": cross_border,
    }


def test_cross_border_ratio_30d_returns_correct_ratio() -> None:
    assert calculate_cross_border_ratio_30d(_transactions(), "ACC_A", FEATURE_DATE) == 2 / 3


def test_cross_border_ratio_returns_zero_when_there_are_no_transactions() -> None:
    assert calculate_cross_border_ratio_30d(_transactions(), "ACC_Z", FEATURE_DATE) == 0.0


def test_cross_border_ratio_computes_from_countries_when_flag_is_missing() -> None:
    transactions = _transactions().drop(columns=["is_cross_border"])

    assert calculate_cross_border_ratio_30d(transactions, "ACC_A", FEATURE_DATE) == 2 / 3


def test_high_risk_country_exposure_returns_value_weighted_exposure() -> None:
    exposure = calculate_high_risk_country_exposure(
        _transactions(),
        _countries(),
        "ACC_A",
        FEATURE_DATE,
    )

    assert round(exposure, 6) == round((80.0 + 10.0 + 10.0) / 300.0, 6)


def test_high_risk_exposure_uses_risk_score_divided_by_100() -> None:
    exposure = calculate_high_risk_country_exposure(
        _transactions().iloc[[0]],
        _countries(),
        "ACC_A",
        FEATURE_DATE,
    )

    assert exposure == 0.8


def test_high_risk_exposure_handles_missing_risk_scores() -> None:
    transactions = pd.DataFrame(
        [_txn("TXN_VG", "ACC_A", "ACC_B", "2025-01-10T10:00:00Z", 100.0, "US", "VG", True)]
    )

    assert (
        calculate_high_risk_country_exposure(transactions, _countries(), "ACC_A", FEATURE_DATE)
        == 1.0
    )


def test_high_risk_exposure_returns_zero_when_there_is_no_transaction_value() -> None:
    transactions = _transactions().assign(amount=0.0)

    assert (
        calculate_high_risk_country_exposure(transactions, _countries(), "ACC_A", FEATURE_DATE)
        == 0.0
    )


def test_exposure_is_constrained_between_zero_and_one() -> None:
    countries = pd.DataFrame([{"country_code": "PA", "is_high_risk": True, "risk_score": 150.0}])
    transactions = pd.DataFrame(
        [_txn("TXN_1", "ACC_A", "ACC_B", "2025-01-10T10:00:00Z", 100.0, "PA", "PA", True)]
    )

    exposure = calculate_high_risk_country_exposure(transactions, countries, "ACC_A", FEATURE_DATE)

    assert 0.0 <= exposure <= 1.0


def test_calculate_jurisdiction_features_for_date_returns_one_row_per_account() -> None:
    features = calculate_jurisdiction_features_for_date(
        _accounts(),
        _transactions(),
        _countries(),
        FEATURE_DATE,
    )

    assert list(features["account_id"]) == ["ACC_A", "ACC_B"]


def test_input_dataframes_are_not_mutated() -> None:
    accounts = _accounts()
    transactions = _transactions()
    countries = _countries()
    accounts_before = accounts.copy(deep=True)
    transactions_before = transactions.copy(deep=True)
    countries_before = countries.copy(deep=True)

    calculate_jurisdiction_features_for_date(accounts, transactions, countries, FEATURE_DATE)

    pd.testing.assert_frame_equal(accounts, accounts_before)
    pd.testing.assert_frame_equal(transactions, transactions_before)
    pd.testing.assert_frame_equal(countries, countries_before)
