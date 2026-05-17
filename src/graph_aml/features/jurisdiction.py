"""Jurisdiction and country-risk account feature calculations."""

from __future__ import annotations

import pandas as pd

from graph_aml.features.account import AccountFeatureConfig, build_account_universe
from graph_aml.features.exceptions import AccountFeatureError
from graph_aml.features.windows import filter_transactions_for_window, normalise_feature_date

JURISDICTION_FEATURE_COLUMNS = (
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
)


def _prepared(transactions: pd.DataFrame) -> pd.DataFrame:
    from graph_aml.features.account import prepare_transactions_for_features

    return prepare_transactions_for_features(transactions)


def _account_window(
    transactions: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
    window_days: int,
) -> pd.DataFrame:
    prepared = _prepared(transactions)
    if prepared.empty:
        return prepared
    window = filter_transactions_for_window(prepared, feature_date, window_days)
    mask = (window["sender_account_id"] == account_id) | (
        window["receiver_account_id"] == account_id
    )
    return window.loc[mask].copy()


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "t"}
    return bool(value)


def calculate_cross_border_ratio_30d(
    transactions: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
    window_days: int = 30,
) -> float:
    """Return cross-border transaction share for account activity."""

    account_transactions = _account_window(transactions, account_id, feature_date, window_days)
    if account_transactions.empty:
        return 0.0
    if "is_cross_border" in account_transactions.columns:
        cross_border = account_transactions["is_cross_border"].apply(_bool_value)
    else:
        cross_border = account_transactions["origin_country"].astype(str) != account_transactions[
            "destination_country"
        ].astype(str)
    return float(max(0.0, min(1.0, cross_border.sum() / len(account_transactions))))


def _country_weights(countries: pd.DataFrame) -> dict[str, float]:
    weights: dict[str, float] = {}
    for row in countries.copy().to_dict(orient="records"):
        code = str(row.get("country_code", "")).strip().upper()
        if not code:
            continue
        risk_score = pd.to_numeric(pd.Series([row.get("risk_score")]), errors="coerce").iloc[0]
        high_risk = _bool_value(row.get("is_high_risk"))
        if pd.notna(risk_score):
            weight = float(risk_score) / 100.0
        elif high_risk:
            weight = 1.0
        else:
            weight = 0.0
        weights[code] = max(0.0, min(1.0, weight))
    return weights


def _risk_weight_for_country(weights: dict[str, float], value: object) -> float:
    if pd.isna(value):
        return 0.0
    return weights.get(str(value).strip().upper(), 0.0)


def calculate_high_risk_country_exposure(
    transactions: pd.DataFrame,
    countries: pd.DataFrame,
    account_id: str,
    feature_date: pd.Timestamp,
    window_days: int = 30,
) -> float:
    """Return value-weighted high-risk country exposure for account activity."""

    account_transactions = _account_window(transactions, account_id, feature_date, window_days)
    if account_transactions.empty:
        return 0.0
    weights = _country_weights(countries)
    amounts = pd.to_numeric(account_transactions["amount"], errors="coerce").fillna(0.0)
    total_value = float(amounts.sum())
    if total_value <= 0:
        return 0.0
    weighted_value = 0.0
    for amount, origin, destination in zip(
        amounts,
        account_transactions.get("origin_country", pd.Series(index=account_transactions.index)),
        account_transactions.get(
            "destination_country",
            pd.Series(index=account_transactions.index),
        ),
        strict=True,
    ):
        risk_weight = max(
            _risk_weight_for_country(weights, origin),
            _risk_weight_for_country(weights, destination),
        )
        weighted_value += float(amount) * risk_weight
    return float(max(0.0, min(1.0, weighted_value / total_value)))


def calculate_jurisdiction_features_for_date(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    countries: pd.DataFrame,
    feature_date: pd.Timestamp,
    config: AccountFeatureConfig | None = None,
) -> pd.DataFrame:
    """Calculate jurisdiction account features for one feature date."""

    resolved_config = AccountFeatureConfig() if config is None else config
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
                    "cross_border_ratio_30d": calculate_cross_border_ratio_30d(
                        prepared,
                        account_id,
                        feature_day,
                        resolved_config.jurisdiction_window_days,
                    ),
                    "high_risk_country_exposure": calculate_high_risk_country_exposure(
                        prepared,
                        countries,
                        account_id,
                        feature_day,
                        resolved_config.jurisdiction_window_days,
                    ),
                }
            )
        columns = ("account_id", "feature_date", *JURISDICTION_FEATURE_COLUMNS)
        return (
            pd.DataFrame(rows, columns=columns)
            .sort_values("account_id", kind="mergesort")
            .reset_index(drop=True)
        )
    except Exception as exc:
        raise AccountFeatureError(f"Failed to calculate jurisdiction features: {exc}") from exc
