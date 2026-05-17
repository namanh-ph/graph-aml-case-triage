"""Summary helpers for account feature artefacts."""

from __future__ import annotations

import math
from typing import Any, cast

import pandas as pd


def _float_or_zero(value: object) -> float:
    if pd.isna(value):
        return 0.0
    return float(cast(Any, value))


def _iso_date(value: object) -> str | None:
    if pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    return str(timestamp.date())


def summarise_account_features(features: pd.DataFrame) -> dict[str, object]:
    """Return JSON-serialisable summary metrics for account feature rows."""

    summary: dict[str, Any] = {
        "feature_row_count": 0,
        "account_count": 0,
        "feature_version_count": 0,
        "min_feature_date": None,
        "max_feature_date": None,
        "mean_txn_count_7d": 0.0,
        "max_txn_count_7d": 0,
        "mean_total_sent_7d": 0.0,
        "max_total_sent_7d": 0.0,
        "mean_total_received_7d": 0.0,
        "max_total_received_7d": 0.0,
        "mean_unique_counterparties_7d": 0.0,
        "max_unique_counterparties_7d": 0,
        "infinite_in_out_ratio_count": 0,
        "zero_activity_row_count": 0,
    }
    if features.empty:
        _add_extended_summary(features, summary)
        return summary

    txn_count_7d = pd.to_numeric(features["txn_count_7d"], errors="coerce").fillna(0)
    total_sent = pd.to_numeric(features["total_sent_7d"], errors="coerce").fillna(0.0)
    total_received = pd.to_numeric(features["total_received_7d"], errors="coerce").fillna(0.0)
    unique_counterparties = pd.to_numeric(
        features["unique_counterparties_7d"],
        errors="coerce",
    ).fillna(0)
    ratios = pd.to_numeric(features["in_out_ratio_7d"], errors="coerce")
    feature_dates = pd.to_datetime(features["feature_date"], errors="coerce")

    summary.update(
        {
            "feature_row_count": int(len(features)),
            "account_count": int(features["account_id"].nunique(dropna=True)),
            "feature_version_count": int(features["feature_version"].nunique(dropna=True)),
            "min_feature_date": _iso_date(feature_dates.min()),
            "max_feature_date": _iso_date(feature_dates.max()),
            "mean_txn_count_7d": _float_or_zero(txn_count_7d.mean()),
            "max_txn_count_7d": int(txn_count_7d.max()),
            "mean_total_sent_7d": _float_or_zero(total_sent.mean()),
            "max_total_sent_7d": _float_or_zero(total_sent.max()),
            "mean_total_received_7d": _float_or_zero(total_received.mean()),
            "max_total_received_7d": _float_or_zero(total_received.max()),
            "mean_unique_counterparties_7d": _float_or_zero(unique_counterparties.mean()),
            "max_unique_counterparties_7d": int(unique_counterparties.max()),
            "infinite_in_out_ratio_count": int(
                sum(math.isinf(float(value)) for value in ratios.dropna())
            ),
            "zero_activity_row_count": int((txn_count_7d == 0).sum()),
        }
    )
    _add_extended_summary(features, summary)
    return summary


def _add_numeric_summary(
    features: pd.DataFrame,
    summary: dict[str, Any],
    column: str,
    *,
    mean_key: str,
    max_key: str,
    min_key: str | None = None,
) -> None:
    if column not in features.columns:
        return
    values = pd.to_numeric(features[column], errors="coerce")
    if values.dropna().empty:
        summary[mean_key] = 0.0
        summary[max_key] = 0.0
        if min_key is not None:
            summary[min_key] = 0.0
        return
    summary[mean_key] = _float_or_zero(values.mean())
    summary[max_key] = _float_or_zero(values.max())
    if min_key is not None:
        summary[min_key] = _float_or_zero(values.min())


def _add_extended_summary(features: pd.DataFrame, summary: dict[str, Any]) -> None:
    _add_numeric_summary(
        features,
        summary,
        "retained_balance_proxy",
        mean_key="mean_retained_balance_proxy",
        min_key="min_retained_balance_proxy",
        max_key="max_retained_balance_proxy",
    )
    _add_numeric_summary(
        features,
        summary,
        "below_threshold_count_24h",
        mean_key="mean_below_threshold_count_24h",
        max_key="max_below_threshold_count_24h",
    )
    if "dormant_days_before_activity" in features.columns:
        dormant = pd.to_numeric(features["dormant_days_before_activity"], errors="coerce")
        non_null = dormant.dropna()
        summary["dormant_feature_non_null_count"] = int(len(non_null))
        summary["mean_dormant_days_before_activity"] = (
            0.0 if non_null.empty else _float_or_zero(non_null.mean())
        )
        summary["max_dormant_days_before_activity"] = (
            0.0 if non_null.empty else _float_or_zero(non_null.max())
        )
    _add_numeric_summary(
        features,
        summary,
        "cross_border_ratio_30d",
        mean_key="mean_cross_border_ratio_30d",
        max_key="max_cross_border_ratio_30d",
    )
    _add_numeric_summary(
        features,
        summary,
        "high_risk_country_exposure",
        mean_key="mean_high_risk_country_exposure",
        max_key="max_high_risk_country_exposure",
    )
    _add_numeric_summary(
        features,
        summary,
        "counterparty_entropy",
        mean_key="mean_counterparty_entropy",
        max_key="max_counterparty_entropy",
    )
