"""Behavioural account feature calculations."""

from __future__ import annotations

import math

import pandas as pd

from graph_aml.features.account import AccountFeatureConfig, build_account_universe
from graph_aml.features.exceptions import AccountFeatureError, FeatureInputError
from graph_aml.features.windows import filter_transactions_for_window, normalise_feature_date

BEHAVIOURAL_FEATURE_COLUMNS = (
    "retained_balance_proxy",
    "below_threshold_count_24h",
    "dormant_days_before_activity",
    "counterparty_entropy",
)


def _prepared(transactions: pd.DataFrame) -> pd.DataFrame:
    from graph_aml.features.account import prepare_transactions_for_features

    return prepare_transactions_for_features(transactions)


def _account_activity(transactions: pd.DataFrame, account_id: str) -> pd.DataFrame:
    mask = (transactions["sender_account_id"] == account_id) | (
        transactions["receiver_account_id"] == account_id
    )
    return transactions.loc[mask].copy()


def calculate_retained_balance_proxy(
    transactions: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
    window_days: int = 7,
) -> float:
    """Return inbound value minus outbound value for an account in a rolling window."""

    prepared = _prepared(transactions)
    if prepared.empty:
        return 0.0
    window = filter_transactions_for_window(prepared, feature_date, window_days)
    received = window.loc[window["receiver_account_id"] == account_id, "amount"].sum()
    sent = window.loc[window["sender_account_id"] == account_id, "amount"].sum()
    return float(received - sent)


def calculate_below_threshold_count_24h(
    transactions: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
    reporting_threshold: float = 10000.0,
    below_threshold_margin: float = 0.95,
) -> int:
    """Count outbound transactions just below the reporting threshold."""

    if reporting_threshold <= 0:
        raise FeatureInputError("reporting_threshold must be positive")
    if below_threshold_margin <= 0 or below_threshold_margin >= 1:
        raise FeatureInputError("below_threshold_margin must be greater than 0 and less than 1")

    prepared = _prepared(transactions)
    if prepared.empty:
        return 0
    window = filter_transactions_for_window(prepared, feature_date, window_days=1)
    lower_bound = reporting_threshold * below_threshold_margin
    outbound = window[window["sender_account_id"] == account_id]
    near_threshold = (outbound["amount"] >= lower_bound) & (
        outbound["amount"] < reporting_threshold
    )
    return int(near_threshold.sum())


def calculate_dormant_days_before_activity(
    transactions: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
) -> int | None:
    """Return calendar-day inactivity gap before current activity, when measurable."""

    prepared = _prepared(transactions)
    if prepared.empty:
        return None
    feature_day = normalise_feature_date(feature_date)
    current_start = feature_day - pd.Timedelta(days=1)
    current_end = feature_day + pd.Timedelta(days=1)
    account_transactions = _account_activity(prepared, account_id)
    if account_transactions.empty:
        return None

    current = account_transactions[
        account_transactions["transaction_timestamp"].gt(current_start)
        & account_transactions["transaction_timestamp"].le(current_end)
    ]
    if current.empty:
        return None

    prior = account_transactions[account_transactions["transaction_timestamp"].le(current_start)]
    if prior.empty:
        return None

    first_current = pd.Timestamp(current["transaction_timestamp"].min()).normalize()
    most_recent_prior = pd.Timestamp(prior["transaction_timestamp"].max()).normalize()
    return int((first_current - most_recent_prior).days)


def calculate_counterparty_entropy(
    transactions: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
    window_days: int = 30,
) -> float:
    """Return Shannon entropy over outbound recipient keys in a rolling window."""

    prepared = _prepared(transactions)
    if prepared.empty:
        return 0.0
    window = filter_transactions_for_window(prepared, feature_date, window_days)
    outbound = window.loc[window["sender_account_id"] == account_id, "recipient_key"]
    if outbound.empty:
        return 0.0
    counts = outbound.value_counts()
    total = float(counts.sum())
    if total <= 0:
        return 0.0
    entropy = -sum((count / total) * math.log(count / total) for count in counts.astype(float))
    return float(max(0.0, entropy))


def calculate_behavioural_features_for_date(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    feature_date: pd.Timestamp,
    config: AccountFeatureConfig | None = None,
    reporting_threshold: float = 10000.0,
    below_threshold_margin: float = 0.95,
) -> pd.DataFrame:
    """Calculate behavioural account features for one feature date."""

    resolved_config = AccountFeatureConfig() if config is None else config
    threshold = resolved_config.reporting_threshold if config is not None else reporting_threshold
    margin = (
        resolved_config.below_threshold_margin if config is not None else below_threshold_margin
    )
    try:
        prepared = _prepared(transactions)
        universe = build_account_universe(
            accounts,
            prepared,
            include_all_accounts=resolved_config.include_all_accounts,
        )
        feature_day = normalise_feature_date(feature_date)
        rows: list[dict[str, object]] = []
        for account_id in universe["account_id"].astype(str):
            rows.append(
                {
                    "account_id": account_id,
                    "feature_date": feature_day,
                    "retained_balance_proxy": calculate_retained_balance_proxy(
                        prepared,
                        account_id,
                        feature_day,
                        resolved_config.weekly_window_days,
                    ),
                    "below_threshold_count_24h": calculate_below_threshold_count_24h(
                        prepared,
                        account_id,
                        feature_day,
                        threshold,
                        margin,
                    ),
                    "dormant_days_before_activity": calculate_dormant_days_before_activity(
                        prepared,
                        account_id,
                        feature_day,
                    ),
                    "counterparty_entropy": calculate_counterparty_entropy(
                        prepared,
                        account_id,
                        feature_day,
                        resolved_config.entropy_window_days,
                    ),
                }
            )
        columns = ("account_id", "feature_date", *BEHAVIOURAL_FEATURE_COLUMNS)
        return (
            pd.DataFrame(rows, columns=columns)
            .sort_values("account_id", kind="mergesort")
            .reset_index(drop=True)
        )
    except FeatureInputError:
        raise
    except Exception as exc:
        raise AccountFeatureError(f"Failed to calculate behavioural features: {exc}") from exc
