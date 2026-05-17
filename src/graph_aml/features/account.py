"""Account-level behavioural feature engineering."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from graph_aml.features.exceptions import AccountFeatureError, FeatureInputError
from graph_aml.features.windows import (
    build_feature_date_range,
    filter_transactions_for_window,
    normalise_feature_date,
)

ACCOUNT_FEATURE_COLUMNS = (
    "account_id",
    "feature_date",
    "feature_version",
    "txn_count_1d",
    "txn_count_7d",
    "total_sent_7d",
    "total_received_7d",
    "avg_txn_amount_30d",
    "max_txn_amount_30d",
    "unique_counterparties_7d",
    "in_out_ratio_7d",
)
EXTENDED_ACCOUNT_FEATURE_COLUMNS = (
    "account_id",
    "feature_date",
    "feature_version",
    "txn_count_1d",
    "txn_count_7d",
    "total_sent_7d",
    "total_received_7d",
    "avg_txn_amount_30d",
    "max_txn_amount_30d",
    "unique_counterparties_7d",
    "in_out_ratio_7d",
    "retained_balance_proxy",
    "below_threshold_count_24h",
    "dormant_days_before_activity",
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
    "counterparty_entropy",
)
ACCOUNT_UNIVERSE_COLUMNS = (
    "account_id",
    "customer_id",
    "account_type",
    "account_status",
    "currency",
    "home_country",
)
REQUIRED_TRANSACTION_COLUMNS = (
    "transaction_id",
    "sender_account_id",
    "receiver_account_id",
    "counterparty_id",
    "transaction_timestamp",
    "amount",
)
IN_OUT_RATIO_RECEIVED_ZERO_CAP = 999999.0


@dataclass(frozen=True)
class AccountFeatureConfig:
    """Configuration for account-level feature generation."""

    feature_version: str = "account_features_v1"
    daily_window_days: int = 1
    weekly_window_days: int = 7
    monthly_window_days: int = 30
    min_feature_date: str | None = None
    max_feature_date: str | None = None
    include_all_accounts: bool = True
    reporting_threshold: float = 10000.0
    below_threshold_margin: float = 0.95
    entropy_window_days: int = 30
    jurisdiction_window_days: int = 30

    def __post_init__(self) -> None:
        if self.daily_window_days <= 0:
            raise ValueError("daily_window_days must be positive")
        if self.weekly_window_days <= 0:
            raise ValueError("weekly_window_days must be positive")
        if self.monthly_window_days <= 0:
            raise ValueError("monthly_window_days must be positive")
        if self.weekly_window_days < self.daily_window_days:
            raise ValueError(
                "weekly_window_days must be greater than or equal to daily_window_days"
            )
        if self.monthly_window_days < self.weekly_window_days:
            raise ValueError(
                "monthly_window_days must be greater than or equal to weekly_window_days"
            )
        if self.min_feature_date is not None and self.max_feature_date is not None:
            if normalise_feature_date(self.min_feature_date) > normalise_feature_date(
                self.max_feature_date
            ):
                raise ValueError("min_feature_date must be less than or equal to max_feature_date")
        if self.reporting_threshold <= 0:
            raise ValueError("reporting_threshold must be positive")
        if self.below_threshold_margin <= 0 or self.below_threshold_margin >= 1:
            raise ValueError("below_threshold_margin must be greater than 0 and less than 1")
        if self.entropy_window_days <= 0:
            raise ValueError("entropy_window_days must be positive")
        if self.jurisdiction_window_days <= 0:
            raise ValueError("jurisdiction_window_days must be positive")


def _empty_features() -> pd.DataFrame:
    return pd.DataFrame(columns=ACCOUNT_FEATURE_COLUMNS)


def _empty_extended_features() -> pd.DataFrame:
    return pd.DataFrame(columns=EXTENDED_ACCOUNT_FEATURE_COLUMNS)


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], label: str) -> None:
    missing = set(columns).difference(frame.columns)
    if missing:
        raise FeatureInputError(f"{label} is missing required columns: {sorted(missing)}")


def _normalise_account_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"nan", "none", "null"}:
            return None
        return stripped.upper()
    if pd.isna(value):
        return None
    return str(value).strip().upper()


def _recipient_key(row: pd.Series) -> str:
    receiver = _normalise_account_id(row.get("receiver_account_id"))
    if receiver is not None:
        return receiver
    counterparty = _normalise_account_id(row.get("counterparty_id"))
    if counterparty is not None:
        return counterparty
    return "<missing_recipient>"


def _stable_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output.loc[:, columns]


def build_account_universe(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    include_all_accounts: bool = True,
) -> pd.DataFrame:
    """Build one account-universe row per account ID."""

    try:
        if include_all_accounts:
            if "account_id" not in accounts.columns:
                raise FeatureInputError("accounts is missing account_id")
            universe = _stable_columns(accounts, ACCOUNT_UNIVERSE_COLUMNS).copy()
            universe["account_id"] = universe["account_id"].apply(_normalise_account_id)
            universe = universe[universe["account_id"].notna()]
        else:
            account_ids: set[str] = set()
            if "sender_account_id" in transactions.columns:
                account_ids.update(
                    value
                    for value in transactions["sender_account_id"].apply(_normalise_account_id)
                    if value is not None
                )
            if "receiver_account_id" in transactions.columns:
                account_ids.update(
                    value
                    for value in transactions["receiver_account_id"].apply(_normalise_account_id)
                    if value is not None
                )
            universe = pd.DataFrame({"account_id": sorted(account_ids)})
            if "account_id" in accounts.columns and not accounts.empty:
                account_lookup = _stable_columns(accounts, ACCOUNT_UNIVERSE_COLUMNS).copy()
                account_lookup["account_id"] = account_lookup["account_id"].apply(
                    _normalise_account_id
                )
                universe = universe.merge(
                    account_lookup.drop_duplicates("account_id"),
                    on="account_id",
                    how="left",
                )
            else:
                for column in ACCOUNT_UNIVERSE_COLUMNS:
                    if column != "account_id":
                        universe[column] = pd.NA

        if universe.empty:
            raise FeatureInputError("No account IDs could be resolved")
        return (
            universe.drop_duplicates("account_id", keep="last")
            .sort_values("account_id", kind="mergesort")
            .reset_index(drop=True)
        )
    except FeatureInputError:
        raise
    except Exception as exc:
        raise FeatureInputError(f"Failed to build account universe: {exc}") from exc


def prepare_transactions_for_features(transactions: pd.DataFrame) -> pd.DataFrame:
    """Prepare staging transactions for deterministic feature calculation."""

    _require_columns(transactions, REQUIRED_TRANSACTION_COLUMNS, "transactions")
    try:
        frame = transactions.copy()
        frame["transaction_id"] = frame["transaction_id"].apply(_normalise_account_id)
        frame["sender_account_id"] = frame["sender_account_id"].apply(_normalise_account_id)
        frame["receiver_account_id"] = frame["receiver_account_id"].apply(_normalise_account_id)
        frame["counterparty_id"] = frame["counterparty_id"].apply(_normalise_account_id)
        frame["transaction_timestamp"] = pd.to_datetime(
            frame["transaction_timestamp"],
            utc=True,
            errors="coerce",
        )
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
        frame = frame[
            frame["transaction_id"].notna()
            & frame["sender_account_id"].notna()
            & frame["transaction_timestamp"].notna()
            & frame["amount"].notna()
            & (frame["amount"] > 0)
        ].copy()
        if frame.empty:
            frame["recipient_key"] = pd.Series(dtype=object)
            return frame.reset_index(drop=True)
        frame["recipient_key"] = frame.apply(_recipient_key, axis=1)
        return frame.sort_values(
            ["transaction_timestamp", "transaction_id"],
            kind="mergesort",
        ).reset_index(drop=True)
    except FeatureInputError:
        raise
    except Exception as exc:
        raise FeatureInputError(f"Failed to prepare transactions for features: {exc}") from exc


def _count_activity(frame: pd.DataFrame, account_id: str) -> int:
    mask = (frame["sender_account_id"] == account_id) | (frame["receiver_account_id"] == account_id)
    return int(mask.sum())


def _sent_total(frame: pd.DataFrame, account_id: str) -> float:
    return float(frame.loc[frame["sender_account_id"] == account_id, "amount"].sum())


def _received_total(frame: pd.DataFrame, account_id: str) -> float:
    return float(frame.loc[frame["receiver_account_id"] == account_id, "amount"].sum())


def _amounts_for_account(frame: pd.DataFrame, account_id: str) -> pd.Series:
    mask = (frame["sender_account_id"] == account_id) | (frame["receiver_account_id"] == account_id)
    return frame.loc[mask, "amount"]


def _unique_counterparties(frame: pd.DataFrame, account_id: str) -> int:
    outbound = set(frame.loc[frame["sender_account_id"] == account_id, "recipient_key"].dropna())
    inbound = set(
        frame.loc[frame["receiver_account_id"] == account_id, "sender_account_id"].dropna()
    )
    return len(outbound | inbound)


def _in_out_ratio(sent_total: float, received_total: float) -> float:
    if received_total > 0:
        return float(sent_total / received_total)
    if sent_total > 0:
        return IN_OUT_RATIO_RECEIVED_ZERO_CAP
    return 0.0


def calculate_features_for_date(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    feature_date: pd.Timestamp,
    config: AccountFeatureConfig | None = None,
) -> pd.DataFrame:
    """Calculate account features for one feature date."""

    resolved_config = AccountFeatureConfig() if config is None else config
    try:
        prepared = prepare_transactions_for_features(transactions)
        universe = build_account_universe(
            accounts,
            prepared,
            include_all_accounts=resolved_config.include_all_accounts,
        )
        feature_day = normalise_feature_date(feature_date)
        day_window = filter_transactions_for_window(
            prepared,
            feature_day,
            resolved_config.daily_window_days,
        )
        week_window = filter_transactions_for_window(
            prepared,
            feature_day,
            resolved_config.weekly_window_days,
        )
        month_window = filter_transactions_for_window(
            prepared,
            feature_day,
            resolved_config.monthly_window_days,
        )
        rows: list[dict[str, object]] = []
        for account_id in universe["account_id"].astype(str):
            sent_total = _sent_total(week_window, account_id)
            received_total = _received_total(week_window, account_id)
            month_amounts = _amounts_for_account(month_window, account_id)
            rows.append(
                {
                    "account_id": account_id,
                    "feature_date": feature_day,
                    "feature_version": resolved_config.feature_version,
                    "txn_count_1d": _count_activity(day_window, account_id),
                    "txn_count_7d": _count_activity(week_window, account_id),
                    "total_sent_7d": sent_total,
                    "total_received_7d": received_total,
                    "avg_txn_amount_30d": (
                        0.0 if month_amounts.empty else float(month_amounts.mean())
                    ),
                    "max_txn_amount_30d": (
                        0.0 if month_amounts.empty else float(month_amounts.max())
                    ),
                    "unique_counterparties_7d": _unique_counterparties(week_window, account_id),
                    "in_out_ratio_7d": _in_out_ratio(sent_total, received_total),
                }
            )
        output = pd.DataFrame(rows, columns=ACCOUNT_FEATURE_COLUMNS)
        return output.sort_values("account_id", kind="mergesort").reset_index(drop=True)
    except FeatureInputError:
        raise
    except Exception as exc:
        raise AccountFeatureError(f"Failed to calculate account features: {exc}") from exc


def calculate_account_features(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    config: AccountFeatureConfig | None = None,
) -> pd.DataFrame:
    """Calculate daily account feature rows for all feature dates."""

    resolved_config = AccountFeatureConfig() if config is None else config
    try:
        prepared = prepare_transactions_for_features(transactions)
        if prepared.empty:
            return _empty_features()
        feature_dates = build_feature_date_range(
            prepared,
            min_feature_date=resolved_config.min_feature_date,
            max_feature_date=resolved_config.max_feature_date,
        )
        if len(feature_dates) == 0:
            return _empty_features()
        frames = [
            calculate_features_for_date(accounts, prepared, feature_date, resolved_config)
            for feature_date in feature_dates
        ]
        features = pd.concat(frames, ignore_index=True) if frames else _empty_features()
        if features.empty:
            return _empty_features()
        features = features.loc[:, ACCOUNT_FEATURE_COLUMNS].sort_values(
            ["feature_date", "account_id"],
            kind="mergesort",
        )
        return features.reset_index(drop=True)
    except FeatureInputError:
        raise
    except AccountFeatureError:
        raise
    except Exception as exc:
        raise AccountFeatureError(f"Failed to calculate account feature table: {exc}") from exc


def calculate_extended_features_for_date(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    countries: pd.DataFrame,
    feature_date: pd.Timestamp,
    config: AccountFeatureConfig | None = None,
) -> pd.DataFrame:
    """Calculate base, behavioural, and jurisdiction features for one feature date."""

    resolved_config = AccountFeatureConfig() if config is None else config
    try:
        from graph_aml.features.behavioural import calculate_behavioural_features_for_date
        from graph_aml.features.jurisdiction import calculate_jurisdiction_features_for_date

        base = calculate_features_for_date(accounts, transactions, feature_date, resolved_config)
        behavioural = calculate_behavioural_features_for_date(
            accounts,
            transactions,
            feature_date,
            resolved_config,
        )
        jurisdiction = calculate_jurisdiction_features_for_date(
            accounts,
            transactions,
            countries,
            feature_date,
            resolved_config,
        )
        output = base.merge(
            behavioural,
            on=["account_id", "feature_date"],
            how="left",
        ).merge(
            jurisdiction,
            on=["account_id", "feature_date"],
            how="left",
        )
        fill_zero_columns = (
            "retained_balance_proxy",
            "below_threshold_count_24h",
            "cross_border_ratio_30d",
            "high_risk_country_exposure",
            "counterparty_entropy",
        )
        for column in fill_zero_columns:
            output[column] = output[column].fillna(0)
        output["dormant_days_before_activity"] = pd.to_numeric(
            output["dormant_days_before_activity"],
            errors="coerce",
        ).astype("Int64")
        output = output.loc[:, EXTENDED_ACCOUNT_FEATURE_COLUMNS]
        return output.sort_values("account_id", kind="mergesort").reset_index(drop=True)
    except FeatureInputError:
        raise
    except Exception as exc:
        raise AccountFeatureError(f"Failed to calculate extended account features: {exc}") from exc


def calculate_extended_account_features(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    countries: pd.DataFrame,
    config: AccountFeatureConfig | None = None,
) -> pd.DataFrame:
    """Calculate daily extended account feature rows for all feature dates."""

    resolved_config = AccountFeatureConfig() if config is None else config
    try:
        prepared = prepare_transactions_for_features(transactions)
        if prepared.empty:
            return _empty_extended_features()
        feature_dates = build_feature_date_range(
            prepared,
            min_feature_date=resolved_config.min_feature_date,
            max_feature_date=resolved_config.max_feature_date,
        )
        if len(feature_dates) == 0:
            return _empty_extended_features()
        frames = [
            calculate_extended_features_for_date(
                accounts,
                prepared,
                countries,
                feature_date,
                resolved_config,
            )
            for feature_date in feature_dates
        ]
        features = pd.concat(frames, ignore_index=True) if frames else _empty_extended_features()
        if features.empty:
            return _empty_extended_features()
        features = features.loc[:, EXTENDED_ACCOUNT_FEATURE_COLUMNS].sort_values(
            ["feature_date", "account_id"],
            kind="mergesort",
        )
        return features.reset_index(drop=True)
    except FeatureInputError:
        raise
    except AccountFeatureError:
        raise
    except Exception as exc:
        raise AccountFeatureError(
            f"Failed to calculate extended account feature table: {exc}"
        ) from exc


def _require_feature_columns(features: pd.DataFrame) -> None:
    missing = set(ACCOUNT_FEATURE_COLUMNS).difference(features.columns)
    if missing:
        raise AccountFeatureError(f"features is missing required columns: {sorted(missing)}")


def _require_extended_feature_columns(features: pd.DataFrame) -> None:
    missing = set(EXTENDED_ACCOUNT_FEATURE_COLUMNS).difference(features.columns)
    if missing:
        raise AccountFeatureError(
            f"extended features is missing required columns: {sorted(missing)}"
        )


def _numeric_series(features: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(features[column], errors="coerce")


def validate_account_features(features: pd.DataFrame) -> None:
    """Validate account feature table shape and core constraints."""

    try:
        _require_feature_columns(features)
        if features.empty:
            return
        for column in ("account_id", "feature_date", "feature_version"):
            if features[column].isna().any():
                raise AccountFeatureError(f"{column} must be non-null")

        count_columns = ("txn_count_1d", "txn_count_7d", "unique_counterparties_7d")
        for column in count_columns:
            values = _numeric_series(features, column)
            if values.isna().any() or (values < 0).any() or (values % 1 != 0).any():
                raise AccountFeatureError(f"{column} must contain non-negative integers")

        non_negative_columns = (
            "total_sent_7d",
            "total_received_7d",
            "avg_txn_amount_30d",
            "max_txn_amount_30d",
            "in_out_ratio_7d",
        )
        for column in non_negative_columns:
            values = _numeric_series(features, column)
            if values.isna().any() or (values < 0).any():
                raise AccountFeatureError(f"{column} must be non-negative")

        duplicate_count = features.duplicated(
            subset=["account_id", "feature_date", "feature_version"]
        ).sum()
        if duplicate_count:
            raise AccountFeatureError(
                "account_id, feature_date, and feature_version must be unique"
            )
    except AccountFeatureError:
        raise
    except Exception as exc:
        raise AccountFeatureError(f"Failed to validate account features: {exc}") from exc


def validate_extended_account_features(features: pd.DataFrame) -> None:
    """Validate extended account feature rows."""

    try:
        _require_extended_feature_columns(features)
        validate_account_features(features.loc[:, list(ACCOUNT_FEATURE_COLUMNS)])
        if features.empty:
            return

        count_columns = ("below_threshold_count_24h",)
        for column in count_columns:
            values = _numeric_series(features, column)
            if values.isna().any() or (values < 0).any() or (values % 1 != 0).any():
                raise AccountFeatureError(f"{column} must contain non-negative integers")

        non_negative_columns = (
            "cross_border_ratio_30d",
            "high_risk_country_exposure",
            "counterparty_entropy",
        )
        for column in non_negative_columns:
            values = _numeric_series(features, column)
            if values.isna().any() or (values < 0).any():
                raise AccountFeatureError(f"{column} must be non-negative")

        for column in ("cross_border_ratio_30d", "high_risk_country_exposure"):
            values = _numeric_series(features, column)
            if (values > 1).any():
                raise AccountFeatureError(f"{column} must be between 0.0 and 1.0")

        retained = _numeric_series(features, "retained_balance_proxy")
        if retained.isna().any():
            raise AccountFeatureError("retained_balance_proxy must be numeric")

        dormant = _numeric_series(features, "dormant_days_before_activity").dropna()
        if (dormant < 0).any() or (dormant % 1 != 0).any():
            raise AccountFeatureError(
                "dormant_days_before_activity must be null or a non-negative integer"
            )
    except AccountFeatureError:
        raise
    except Exception as exc:
        raise AccountFeatureError(f"Failed to validate extended account features: {exc}") from exc
