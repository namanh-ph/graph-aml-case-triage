"""Feature date and rolling-window helpers."""

from __future__ import annotations

import pandas as pd

from graph_aml.features.exceptions import FeatureInputError


def normalise_feature_date(value: object) -> pd.Timestamp:
    """Normalise a value to a UTC midnight feature date."""

    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise FeatureInputError(f"Invalid feature date: {value}")
    return pd.Timestamp(timestamp).normalize()


def build_feature_date_range(
    transactions: pd.DataFrame,
    min_feature_date: str | None = None,
    max_feature_date: str | None = None,
) -> pd.DatetimeIndex:
    """Build a deterministic daily feature date range."""

    if min_feature_date is not None:
        start = normalise_feature_date(min_feature_date)
    else:
        if transactions.empty or "transaction_timestamp" not in transactions.columns:
            return pd.DatetimeIndex([], tz="UTC")
        timestamps = pd.to_datetime(
            transactions["transaction_timestamp"],
            utc=True,
            errors="coerce",
        ).dropna()
        if timestamps.empty:
            return pd.DatetimeIndex([], tz="UTC")
        start = pd.Timestamp(timestamps.min()).normalize()

    if max_feature_date is not None:
        end = normalise_feature_date(max_feature_date)
    else:
        timestamps = pd.to_datetime(
            transactions["transaction_timestamp"],
            utc=True,
            errors="coerce",
        ).dropna()
        if timestamps.empty:
            end = start
        else:
            end = pd.Timestamp(timestamps.max()).normalize()

    if start > end:
        raise FeatureInputError("min_feature_date must be less than or equal to max_feature_date")
    return pd.date_range(start=start, end=end, freq="D", tz="UTC")


def filter_transactions_for_window(
    transactions: pd.DataFrame,
    feature_date: pd.Timestamp,
    window_days: int,
    timestamp_column: str = "transaction_timestamp",
) -> pd.DataFrame:
    """Return transactions inside a rolling feature window."""

    if window_days <= 0:
        raise FeatureInputError("window_days must be positive")
    if timestamp_column not in transactions.columns:
        raise FeatureInputError(f"transactions is missing {timestamp_column}")

    feature_day = normalise_feature_date(feature_date)
    timestamps = pd.to_datetime(transactions[timestamp_column], utc=True, errors="coerce")
    start = feature_day - pd.Timedelta(days=window_days)
    end = feature_day + pd.Timedelta(days=1)
    mask = timestamps.gt(start) & timestamps.le(end)
    output = transactions.loc[mask].copy()
    output[timestamp_column] = timestamps.loc[mask]
    sort_columns = [timestamp_column]
    if "transaction_id" in output.columns:
        sort_columns.append("transaction_id")
    return output.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
