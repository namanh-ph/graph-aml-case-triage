"""Feature input readers and matrix frame builders for anomaly models."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.models.config import IsolationForestModelConfig
from graph_aml.models.exceptions import ModelFeatureInputError

ACCOUNT_FEATURE_KEY_COLUMNS = (
    "account_id",
    "feature_date",
)

GRAPH_FEATURE_KEY_COLUMNS = (
    "account_id",
    "feature_date",
)

MODEL_ACCOUNT_BEHAVIOURAL_FEATURES = (
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
)

MODEL_ACCOUNT_JURISDICTION_FEATURES = (
    "cross_border_ratio_30d",
    "high_risk_country_exposure",
)

MODEL_GRAPH_FEATURES = (
    "degree",
    "in_degree",
    "out_degree",
    "degree_centrality",
    "in_degree_centrality",
    "out_degree_centrality",
    "pagerank_score",
    "betweenness_centrality",
    "clustering_coefficient",
    "community_size",
    "cycle_count",
    "fan_in_count",
    "fan_out_count",
    "alert_count",
    "high_risk_alert_count",
    "neighbour_account_count",
    "counterparty_count",
    "transaction_count",
    "total_sent_amount",
    "total_received_amount",
    "graph_component_size",
)

ACCOUNT_FEATURE_TABLE = "mart.features_account_daily"
GRAPH_FEATURE_TABLE = "mart.graph_features"


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise ModelFeatureInputError("limit must be non-negative")
    return int(limit)


def read_model_account_features(
    engine: Engine,
    feature_date: str | None = None,
    feature_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read account behavioural and jurisdiction features for model training."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if feature_date is None:
        clauses.append("feature_date = (SELECT MAX(feature_date) FROM mart.features_account_daily)")
    else:
        clauses.append("feature_date = :feature_date")
        params["feature_date"] = feature_date
    if feature_version is not None:
        clauses.append("feature_version = :feature_version")
        params["feature_version"] = feature_version
    sql = f"SELECT * FROM {ACCOUNT_FEATURE_TABLE} WHERE {' AND '.join(clauses)}"
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ModelFeatureInputError(f"Failed to read account model features: {exc}") from exc


def read_model_graph_features(
    engine: Engine,
    feature_date: str | None = None,
    feature_version: str | None = None,
    graph_build_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read persisted graph features for model training."""

    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if feature_date is not None:
        clauses.append("feature_date = :feature_date")
        params["feature_date"] = feature_date
    if feature_version is not None:
        clauses.append("feature_version = :feature_version")
        params["feature_version"] = feature_version
    if graph_build_id is not None:
        clauses.append("graph_build_id = :graph_build_id")
        params["graph_build_id"] = graph_build_id
    sql = f"SELECT * FROM {GRAPH_FEATURE_TABLE}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    elif feature_date is None and feature_version is None and graph_build_id is None:
        sql = f"""
            WITH latest AS (
                SELECT feature_date, feature_version, graph_build_id
                FROM {GRAPH_FEATURE_TABLE}
                ORDER BY computed_at DESC, feature_date DESC, feature_version, graph_build_id
                LIMIT 1
            )
            SELECT gf.*
            FROM {GRAPH_FEATURE_TABLE} gf
            JOIN latest
              ON gf.feature_date = latest.feature_date
             AND gf.feature_version = latest.feature_version
             AND gf.graph_build_id = latest.graph_build_id
        """
    sql += " ORDER BY account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise ModelFeatureInputError(f"Failed to read graph model features: {exc}") from exc


def read_model_feature_inputs(
    engine: Engine,
    config: IsolationForestModelConfig | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read all feature inputs needed by the configured anomaly model."""

    resolved = IsolationForestModelConfig() if config is None else config
    feature_date = resolved.feature_date.isoformat() if resolved.feature_date else None
    account_features = read_model_account_features(
        engine,
        feature_date=feature_date,
        feature_version=resolved.account_feature_version,
        limit=limit,
    )
    graph_features = pd.DataFrame()
    if resolved.use_graph_features:
        graph_features = read_model_graph_features(
            engine,
            feature_date=feature_date,
            feature_version=resolved.graph_feature_version,
            graph_build_id=resolved.graph_build_id,
            limit=limit,
        )
    return {"account_features": account_features, "graph_features": graph_features}


def select_model_feature_columns(
    config: IsolationForestModelConfig | None = None,
) -> tuple[str, ...]:
    """Return selected feature columns in deterministic order."""

    resolved = IsolationForestModelConfig() if config is None else config
    columns: list[str] = []
    if resolved.use_behavioural_features:
        columns.extend(MODEL_ACCOUNT_BEHAVIOURAL_FEATURES)
    if resolved.use_jurisdiction_features:
        columns.extend(MODEL_ACCOUNT_JURISDICTION_FEATURES)
    if resolved.use_graph_features:
        columns.extend(MODEL_GRAPH_FEATURES)
    return tuple(dict.fromkeys(columns))


def _normalise_account_id_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if "account_id" not in frame.columns:
        raise ModelFeatureInputError("feature frame must include account_id")
    output = frame.copy()
    output["account_id"] = output["account_id"].astype("string").str.strip()
    if output["account_id"].isna().any() or (output["account_id"] == "").any():
        raise ModelFeatureInputError("account_id values must be non-null")
    if output["account_id"].duplicated().any():
        raise ModelFeatureInputError("account_id values must be unique")
    return output


def _prepare_feature_subset(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    output = _normalise_account_id_frame(frame)
    present = [column for column in columns if column in output.columns]
    prepared = output.loc[:, ["account_id", *present]].copy()
    for column in present:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    return prepared


def prepare_account_feature_frame(
    account_features: pd.DataFrame,
    config: IsolationForestModelConfig | None = None,
) -> pd.DataFrame:
    """Prepare account feature rows without imputation or scaling."""

    resolved = IsolationForestModelConfig() if config is None else config
    columns: list[str] = []
    if resolved.use_behavioural_features:
        columns.extend(MODEL_ACCOUNT_BEHAVIOURAL_FEATURES)
    if resolved.use_jurisdiction_features:
        columns.extend(MODEL_ACCOUNT_JURISDICTION_FEATURES)
    return _prepare_feature_subset(account_features, tuple(columns))


def prepare_graph_feature_frame(
    graph_features: pd.DataFrame,
    config: IsolationForestModelConfig | None = None,
) -> pd.DataFrame:
    """Prepare graph feature rows without imputation or scaling."""

    resolved = IsolationForestModelConfig() if config is None else config
    if not resolved.use_graph_features:
        return pd.DataFrame(columns=["account_id"])
    if graph_features.empty and "account_id" not in graph_features.columns:
        return pd.DataFrame(columns=["account_id", *MODEL_GRAPH_FEATURES])
    return _prepare_feature_subset(graph_features, MODEL_GRAPH_FEATURES)


def build_model_feature_frame(
    account_features: pd.DataFrame,
    graph_features: pd.DataFrame | None = None,
    config: IsolationForestModelConfig | None = None,
) -> pd.DataFrame:
    """Build the account-level model feature frame."""

    resolved = IsolationForestModelConfig() if config is None else config
    account_frame = prepare_account_feature_frame(account_features, resolved)
    if resolved.use_graph_features:
        graph_frame = prepare_graph_feature_frame(
            pd.DataFrame() if graph_features is None else graph_features,
            resolved,
        )
        if "account_id" in graph_frame.columns and len(graph_frame.columns) > 1:
            output = account_frame.merge(graph_frame, on="account_id", how="left")
        else:
            output = account_frame.copy()
    else:
        output = account_frame.copy()

    selected = [column for column in select_model_feature_columns(resolved) if column in output]
    if not selected:
        raise ModelFeatureInputError("no usable model feature columns are available")
    output = output.loc[:, ["account_id", *selected]].copy()
    for column in selected:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.replace([np.inf, -np.inf], np.nan)
    output = output.sort_values("account_id").reset_index(drop=True)
    return output
