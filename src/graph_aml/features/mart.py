"""Read persisted account features from mart tables."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.features.exceptions import MartFeatureReadError
from graph_aml.features.persistence import MART_ACCOUNT_FEATURE_TABLE


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise MartFeatureReadError("limit must be non-negative")
    return int(limit)


def read_mart_account_features(
    engine: Engine,
    feature_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read persisted account features ordered by feature date and account ID."""

    safe_limit = _validate_limit(limit)
    sql = f"""
        SELECT *
        FROM {MART_ACCOUNT_FEATURE_TABLE}
    """
    params: dict[str, object] = {}
    if feature_version is not None:
        sql += " WHERE feature_version = :feature_version"
        params["feature_version"] = feature_version
    sql += " ORDER BY feature_date, account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise MartFeatureReadError(f"Failed to read mart account features: {exc}") from exc


def get_mart_account_feature_versions(engine: Engine) -> tuple[str, ...]:
    """Return sorted feature versions persisted in mart.features_account_daily."""

    try:
        frame = pd.read_sql_query(
            text(
                f"""
                SELECT DISTINCT feature_version
                FROM {MART_ACCOUNT_FEATURE_TABLE}
                WHERE feature_version IS NOT NULL
                ORDER BY feature_version
                """
            ),
            engine,
        )
        return tuple(sorted(str(value) for value in frame["feature_version"].dropna().unique()))
    except Exception as exc:
        raise MartFeatureReadError(f"Failed to read mart feature versions: {exc}") from exc


def get_mart_account_feature_date_range(
    engine: Engine,
    feature_version: str | None = None,
) -> dict[str, str | None]:
    """Return min and max persisted feature dates."""

    sql = f"""
        SELECT
            MIN(feature_date) AS min_feature_date,
            MAX(feature_date) AS max_feature_date
        FROM {MART_ACCOUNT_FEATURE_TABLE}
    """
    params: dict[str, object] = {}
    if feature_version is not None:
        sql += " WHERE feature_version = :feature_version"
        params["feature_version"] = feature_version
    try:
        frame = pd.read_sql_query(text(sql), engine, params=params or None)
        if frame.empty:
            return {"min_feature_date": None, "max_feature_date": None}
        return {
            "min_feature_date": _date_string(frame.loc[0, "min_feature_date"]),
            "max_feature_date": _date_string(frame.loc[0, "max_feature_date"]),
        }
    except Exception as exc:
        raise MartFeatureReadError(f"Failed to read mart feature date range: {exc}") from exc


def _date_string(value: object) -> str | None:
    if pd.isna(value):
        return None
    return str(pd.Timestamp(value).date())
