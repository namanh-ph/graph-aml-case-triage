"""Read staged PostgreSQL inputs for account feature engineering."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.features.account import (
    AccountFeatureConfig,
    calculate_account_features,
    calculate_extended_account_features,
)
from graph_aml.features.exceptions import StagedFeatureReadError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise StagedFeatureReadError("limit must be non-negative")
    return int(limit)


def read_staged_accounts_for_features(engine: Engine) -> pd.DataFrame:
    """Read staging.accounts for feature engineering."""

    try:
        return pd.read_sql_query(
            text(
                """
                SELECT
                    account_id,
                    customer_id,
                    account_type,
                    account_status,
                    currency,
                    home_country
                FROM staging.accounts
                ORDER BY account_id
                """
            ),
            engine,
        )
    except Exception as exc:
        raise StagedFeatureReadError(f"Failed to read staging.accounts: {exc}") from exc


def read_staged_transactions_for_features(
    engine: Engine,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read staging.transactions for feature engineering."""

    safe_limit = _validate_limit(limit)
    sql = """
        SELECT
            transaction_id,
            sender_account_id,
            receiver_account_id,
            counterparty_id,
            transaction_timestamp,
            amount,
            origin_country,
            destination_country,
            is_cross_border
        FROM staging.transactions
        ORDER BY transaction_timestamp, transaction_id
    """
    params: dict[str, int] | None = None
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params = {"limit": safe_limit}
    try:
        return pd.read_sql_query(text(sql), engine, params=params)
    except Exception as exc:
        raise StagedFeatureReadError(f"Failed to read staging.transactions: {exc}") from exc


def read_staged_feature_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read staged accounts and transactions for feature engineering."""

    try:
        accounts = read_staged_accounts_for_features(engine)
        transactions = read_staged_transactions_for_features(engine, limit=limit)
        return accounts, transactions
    except StagedFeatureReadError:
        raise
    except Exception as exc:
        raise StagedFeatureReadError(f"Failed to read staged feature inputs: {exc}") from exc


def calculate_account_features_from_staged(
    engine: Engine,
    config: AccountFeatureConfig | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read staged inputs and calculate account features without writing PostgreSQL."""

    accounts, transactions = read_staged_feature_inputs(engine, limit=limit)
    return calculate_account_features(accounts, transactions, config=config)


def read_staged_countries_for_features(engine: Engine) -> pd.DataFrame:
    """Read staging.countries for jurisdiction feature engineering."""

    try:
        return pd.read_sql_query(
            text(
                """
                SELECT
                    country_code,
                    is_high_risk,
                    risk_score
                FROM staging.countries
                ORDER BY country_code
                """
            ),
            engine,
        )
    except Exception as exc:
        raise StagedFeatureReadError(f"Failed to read staging.countries: {exc}") from exc


def read_staged_extended_feature_inputs(
    engine: Engine,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read staged accounts, transactions, and countries for extended features."""

    try:
        accounts, transactions = read_staged_feature_inputs(engine, limit=limit)
        countries = read_staged_countries_for_features(engine)
        return accounts, transactions, countries
    except StagedFeatureReadError:
        raise
    except Exception as exc:
        raise StagedFeatureReadError(
            f"Failed to read staged extended feature inputs: {exc}"
        ) from exc


def calculate_extended_account_features_from_staged(
    engine: Engine,
    config: AccountFeatureConfig | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read staged inputs and calculate extended account features without PostgreSQL writes."""

    accounts, transactions, countries = read_staged_extended_feature_inputs(engine, limit=limit)
    return calculate_extended_account_features(accounts, transactions, countries, config=config)
