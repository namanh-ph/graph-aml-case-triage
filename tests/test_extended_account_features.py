"""Tests for extended account feature table calculation."""

import pandas as pd
import pytest

from graph_aml.features import (
    ACCOUNT_FEATURE_COLUMNS,
    EXTENDED_ACCOUNT_FEATURE_COLUMNS,
    AccountFeatureConfig,
    calculate_account_features,
    calculate_extended_account_features,
    calculate_extended_features_for_date,
    validate_extended_account_features,
)
from graph_aml.features.exceptions import AccountFeatureError

FEATURE_DATE = pd.Timestamp("2025-01-10T00:00:00Z")


def _accounts() -> pd.DataFrame:
    return pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])


def _countries() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"country_code": "US", "is_high_risk": False, "risk_score": 10.0},
            {"country_code": "PA", "is_high_risk": True, "risk_score": 80.0},
        ]
    )


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _txn("TXN_PRIOR", "ACC_A", None, "CP_OLD", "2025-01-01T12:00:00Z", 10.0, "US", "US"),
            _txn("TXN_1", "ACC_A", "ACC_B", None, "2025-01-10T10:00:00Z", 9600.0, "US", "PA"),
            _txn("TXN_2", "ACC_B", "ACC_A", None, "2025-01-10T11:00:00Z", 1000.0, "PA", "US"),
            _txn("TXN_3", "ACC_A", None, "CP_001", "2025-01-10T12:00:00Z", 50.0, "US", "US"),
        ]
    )


def _txn(
    transaction_id: str,
    sender: str,
    receiver: str | None,
    counterparty: str | None,
    timestamp: str,
    amount: float,
    origin: str,
    destination: str,
) -> dict[str, object]:
    return {
        "transaction_id": transaction_id,
        "sender_account_id": sender,
        "receiver_account_id": receiver,
        "counterparty_id": counterparty,
        "transaction_timestamp": timestamp,
        "amount": amount,
        "origin_country": origin,
        "destination_country": destination,
        "is_cross_border": origin != destination,
    }


def _extended() -> pd.DataFrame:
    return calculate_extended_account_features(
        _accounts(),
        _transactions(),
        _countries(),
        AccountFeatureConfig(min_feature_date="2025-01-10", max_feature_date="2025-01-10"),
    )


def test_extended_account_feature_columns_include_base_behavioural_and_jurisdiction() -> None:
    assert set(ACCOUNT_FEATURE_COLUMNS).issubset(EXTENDED_ACCOUNT_FEATURE_COLUMNS)
    assert "retained_balance_proxy" in EXTENDED_ACCOUNT_FEATURE_COLUMNS
    assert "cross_border_ratio_30d" in EXTENDED_ACCOUNT_FEATURE_COLUMNS


def test_calculate_extended_features_for_date_returns_expected_columns() -> None:
    output = calculate_extended_features_for_date(
        _accounts(),
        _transactions(),
        _countries(),
        FEATURE_DATE,
    )

    assert tuple(output.columns) == EXTENDED_ACCOUNT_FEATURE_COLUMNS


def test_calculate_extended_account_features_returns_non_empty_dataframe_for_valid_inputs() -> None:
    assert not _extended().empty


def test_extended_output_has_unique_account_date_version_rows() -> None:
    features = _extended()

    assert not features.duplicated(["account_id", "feature_date", "feature_version"]).any()


def test_extended_output_is_sorted_by_feature_date_and_account_id() -> None:
    features = _extended()

    assert list(features["account_id"]) == ["ACC_A", "ACC_B"]


def test_extended_features_preserve_base_feature_values() -> None:
    base = calculate_account_features(
        _accounts(),
        _transactions(),
        AccountFeatureConfig(min_feature_date="2025-01-10", max_feature_date="2025-01-10"),
    )
    extended = _extended()

    pd.testing.assert_series_equal(
        base.set_index("account_id").loc["ACC_A", list(ACCOUNT_FEATURE_COLUMNS[3:])],
        extended.set_index("account_id").loc["ACC_A", list(ACCOUNT_FEATURE_COLUMNS[3:])],
        check_names=False,
    )


def test_extended_features_include_retained_balance_proxy() -> None:
    assert "retained_balance_proxy" in _extended().columns


def test_extended_features_include_below_threshold_counts() -> None:
    row = _extended().set_index("account_id").loc["ACC_A"]

    assert row["below_threshold_count_24h"] == 1


def test_extended_features_include_dormant_days() -> None:
    assert "dormant_days_before_activity" in _extended().columns


def test_extended_features_include_cross_border_ratio() -> None:
    assert "cross_border_ratio_30d" in _extended().columns


def test_extended_features_include_high_risk_country_exposure() -> None:
    assert _extended()["high_risk_country_exposure"].max() > 0


def test_extended_features_include_counterparty_entropy() -> None:
    assert "counterparty_entropy" in _extended().columns


def test_validate_extended_account_features_passes_valid_features() -> None:
    validate_extended_account_features(_extended())


def test_validate_extended_account_features_fails_on_missing_extended_columns() -> None:
    with pytest.raises(AccountFeatureError):
        validate_extended_account_features(_extended().drop(columns=["counterparty_entropy"]))


def test_inputs_are_not_mutated() -> None:
    accounts = _accounts()
    transactions = _transactions()
    countries = _countries()
    accounts_before = accounts.copy(deep=True)
    transactions_before = transactions.copy(deep=True)
    countries_before = countries.copy(deep=True)

    calculate_extended_account_features(accounts, transactions, countries)

    pd.testing.assert_frame_equal(accounts, accounts_before)
    pd.testing.assert_frame_equal(transactions, transactions_before)
    pd.testing.assert_frame_equal(countries, countries_before)
