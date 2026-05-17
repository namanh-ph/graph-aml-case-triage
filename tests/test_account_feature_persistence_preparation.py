"""Tests for preparing account features for mart persistence."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from graph_aml.features import (
    MART_ACCOUNT_FEATURE_COLUMNS,
    FeaturePersistenceError,
    prepare_account_features_for_persistence,
)


def _features() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "account_id": "ACC_A",
                "feature_date": "2025-01-01T00:00:00Z",
                "feature_version": "account_features_v1",
                "txn_count_1d": "1",
                "txn_count_7d": 2.0,
                "total_sent_7d": "100.50",
                "total_received_7d": 20,
                "avg_txn_amount_30d": "60.25",
                "max_txn_amount_30d": 100.5,
                "unique_counterparties_7d": "1",
                "in_out_ratio_7d": float("inf"),
                "retained_balance_proxy": -80.5,
                "below_threshold_count_24h": "1",
                "dormant_days_before_activity": None,
                "cross_border_ratio_30d": "0.5",
                "high_risk_country_exposure": 0.8,
                "counterparty_entropy": "0.0",
            }
        ]
    )


def test_prepare_account_features_returns_exact_mart_columns() -> None:
    prepared = prepare_account_features_for_persistence(_features())

    assert tuple(prepared.columns) == MART_ACCOUNT_FEATURE_COLUMNS


def test_prepare_account_features_does_not_mutate_input() -> None:
    features = _features()
    original = features.copy(deep=True)

    prepare_account_features_for_persistence(features)

    pd.testing.assert_frame_equal(features, original)


def test_prepare_account_features_coerces_feature_dates_to_date_values() -> None:
    prepared = prepare_account_features_for_persistence(_features())

    assert isinstance(prepared.loc[0, "feature_date"], date)


def test_prepare_account_features_coerces_count_columns_to_integers() -> None:
    prepared = prepare_account_features_for_persistence(_features())

    assert prepared["txn_count_1d"].dtype == "int64"
    assert prepared.loc[0, "below_threshold_count_24h"] == 1


def test_prepare_account_features_coerces_float_columns() -> None:
    prepared = prepare_account_features_for_persistence(_features())

    assert prepared["total_sent_7d"].dtype == "float64"
    assert prepared.loc[0, "high_risk_country_exposure"] == 0.8


def test_prepare_account_features_caps_infinite_in_out_ratio() -> None:
    prepared = prepare_account_features_for_persistence(_features())

    assert prepared.loc[0, "in_out_ratio_7d"] == 999999.0


def test_prepare_account_features_preserves_nullable_dormant_days() -> None:
    prepared = prepare_account_features_for_persistence(_features())

    assert pd.isna(prepared.loc[0, "dormant_days_before_activity"])


def test_prepare_account_features_raises_for_missing_required_columns() -> None:
    with pytest.raises(FeaturePersistenceError):
        prepare_account_features_for_persistence(_features().drop(columns=["account_id"]))


def test_prepare_account_features_raises_for_duplicate_feature_keys() -> None:
    duplicated = pd.concat([_features(), _features()], ignore_index=True)

    with pytest.raises(FeaturePersistenceError):
        prepare_account_features_for_persistence(duplicated)


def test_prepare_account_features_raises_for_negative_counts() -> None:
    features = _features()
    features.loc[0, "txn_count_7d"] = -1

    with pytest.raises(FeaturePersistenceError):
        prepare_account_features_for_persistence(features)
