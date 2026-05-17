"""Tests for account feature configuration and window helpers."""

import pandas as pd
import pytest

from graph_aml.features import (
    AccountFeatureConfig,
    build_feature_date_range,
    filter_transactions_for_window,
    normalise_feature_date,
)


def test_default_account_feature_config_is_valid() -> None:
    config = AccountFeatureConfig()

    assert config.feature_version == "account_features_v1"
    assert config.daily_window_days == 1
    assert config.weekly_window_days == 7
    assert config.monthly_window_days == 30


def test_invalid_window_values_raise_errors() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(daily_window_days=0)


def test_weekly_window_must_be_at_least_daily_window() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(daily_window_days=7, weekly_window_days=3)


def test_monthly_window_must_be_at_least_weekly_window() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(weekly_window_days=30, monthly_window_days=7)


def test_invalid_min_and_max_feature_date_ordering_raises_errors() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(min_feature_date="2025-01-10", max_feature_date="2025-01-01")


def test_normalise_feature_date_returns_midnight_dates() -> None:
    value = normalise_feature_date("2025-01-02T13:45:00Z")

    assert value.hour == 0
    assert value.minute == 0
    assert value.day == 2


def test_build_feature_date_range_derives_expected_dates_from_transactions() -> None:
    transactions = pd.DataFrame(
        {
            "transaction_timestamp": [
                "2025-01-01T10:00:00Z",
                "2025-01-03T11:00:00Z",
            ]
        }
    )

    date_range = build_feature_date_range(transactions)

    assert [str(value.date()) for value in date_range] == [
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
    ]


def test_filter_transactions_for_window_includes_and_excludes_expected_transactions() -> None:
    transactions = pd.DataFrame(
        {
            "transaction_id": ["start", "inside", "end", "outside"],
            "transaction_timestamp": [
                "2025-01-01T00:00:00Z",
                "2025-01-01T01:00:00Z",
                "2025-01-03T00:00:00Z",
                "2025-01-03T01:00:00Z",
            ],
        }
    )

    window = filter_transactions_for_window(
        transactions,
        pd.Timestamp("2025-01-02T00:00:00Z"),
        window_days=1,
    )

    assert list(window["transaction_id"]) == ["inside", "end"]


def test_valid_reporting_threshold_and_margin_are_accepted() -> None:
    config = AccountFeatureConfig(reporting_threshold=5000.0, below_threshold_margin=0.9)

    assert config.reporting_threshold == 5000.0
    assert config.below_threshold_margin == 0.9


def test_invalid_reporting_threshold_raises_error() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(reporting_threshold=0)


def test_invalid_below_threshold_margin_raises_error() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(below_threshold_margin=1.0)


def test_valid_entropy_and_jurisdiction_windows_are_accepted() -> None:
    config = AccountFeatureConfig(entropy_window_days=14, jurisdiction_window_days=21)

    assert config.entropy_window_days == 14
    assert config.jurisdiction_window_days == 21


def test_invalid_entropy_and_jurisdiction_windows_raise_errors() -> None:
    with pytest.raises(ValueError):
        AccountFeatureConfig(entropy_window_days=0)
    with pytest.raises(ValueError):
        AccountFeatureConfig(jurisdiction_window_days=0)
