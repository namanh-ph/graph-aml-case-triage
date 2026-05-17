"""Model metrics and score readers for dashboard pages."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise DashboardDataError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    safe_params = cast("dict[str, Any] | None", params or None)
    return pd.read_sql_query(text(sql), engine, params=safe_params)


def read_dashboard_model_runs(
    engine: Engine,
    model_name: str | None = None,
    model_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if model_name:
        clauses.append("model_name = :model_name")
        params["model_name"] = model_name
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    sql = "SELECT * FROM governance.model_runs"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC NULLS LAST, model_run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read model runs: {exc}") from exc


def read_dashboard_account_anomaly_scores(
    engine: Engine,
    model_version: str | None = None,
    risk_band: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if risk_band:
        clauses.append("risk_band = :risk_band")
        params["risk_band"] = risk_band
    sql = "SELECT * FROM mart.account_anomaly_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY anomaly_rank ASC NULLS LAST, anomaly_score DESC, account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read anomaly scores: {exc}") from exc


def read_dashboard_account_risk_scores(
    engine: Engine,
    score_version: str | None = None,
    risk_band: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if score_version:
        clauses.append("score_version = :score_version")
        params["score_version"] = score_version
    if risk_band:
        clauses.append("risk_band = :risk_band")
        params["risk_band"] = risk_band
    sql = "SELECT * FROM mart.account_risk_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_rank ASC NULLS LAST, account_risk_score DESC, account_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read account risk scores: {exc}") from exc


def read_dashboard_case_risk_scores(
    engine: Engine,
    score_version: str | None = None,
    risk_band: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if score_version:
        clauses.append("score_version = :score_version")
        params["score_version"] = score_version
    if risk_band:
        clauses.append("risk_band = :risk_band")
        params["risk_band"] = risk_band
    sql = "SELECT * FROM aml.case_risk_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_rank ASC NULLS LAST, case_risk_score DESC, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read case risk scores: {exc}") from exc


def read_dashboard_supervised_model_scores(
    engine: Engine,
    model_version: str | None = None,
    entity_level: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if entity_level:
        clauses.append("entity_level = :entity_level")
        params["entity_level"] = entity_level
    sql = "SELECT * FROM mart.supervised_model_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY risk_rank ASC NULLS LAST, supervised_score DESC, entity_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read supervised model scores: {exc}") from exc


def read_dashboard_supervised_model_runs(
    engine: Engine,
    model_version: str | None = None,
    entity_level: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    clauses: list[str] = []
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if entity_level:
        clauses.append("entity_level = :entity_level")
        params["entity_level"] = entity_level
    sql = "SELECT * FROM governance.supervised_model_runs"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY trained_at DESC NULLS LAST, run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read supervised model runs: {exc}") from exc


def read_dashboard_model_comparison_runs(
    engine: Engine,
    comparison_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.model_comparison_runs"
    if comparison_version:
        sql += " WHERE comparison_version = :comparison_version"
        params["comparison_version"] = comparison_version
    sql += " ORDER BY created_at DESC NULLS LAST, comparison_run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read model comparison runs: {exc}") from exc


def read_dashboard_model_comparison_metrics(
    engine: Engine,
    comparison_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.model_comparison_metrics"
    if comparison_run_id:
        sql += " WHERE comparison_run_id = :comparison_run_id"
        params["comparison_run_id"] = comparison_run_id
    sql += " ORDER BY candidate_name, metric_name, top_k NULLS LAST, threshold NULLS LAST"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read model comparison metrics: {exc}") from exc


def read_dashboard_threshold_recommendations(
    engine: Engine,
    comparison_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.threshold_recommendations"
    if comparison_run_id:
        sql += " WHERE comparison_run_id = :comparison_run_id"
        params["comparison_run_id"] = comparison_run_id
    sql += " ORDER BY created_at DESC NULLS LAST, candidate_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read threshold recommendations: {exc}") from exc


def read_dashboard_champion_challenger_results(
    engine: Engine,
    comparison_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.champion_challenger_results"
    if comparison_run_id:
        sql += " WHERE comparison_run_id = :comparison_run_id"
        params["comparison_run_id"] = comparison_run_id
    sql += " ORDER BY is_champion DESC, selection_rank ASC NULLS LAST, candidate_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read champion challenger results: {exc}") from exc


def read_dashboard_monitoring_runs(
    engine: Engine,
    monitoring_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.monitoring_runs"
    if monitoring_version:
        sql += " WHERE monitoring_version = :monitoring_version"
        params["monitoring_version"] = monitoring_version
    sql += " ORDER BY created_at DESC NULLS LAST, monitoring_run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read monitoring runs: {exc}") from exc


def read_dashboard_drift_metrics(
    engine: Engine,
    monitoring_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.drift_metrics"
    if monitoring_run_id:
        sql += " WHERE monitoring_run_id = :monitoring_run_id"
        params["monitoring_run_id"] = monitoring_run_id
    sql += " ORDER BY drift_band DESC, feature_name, drift_metric"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read drift metrics: {exc}") from exc


def read_dashboard_volume_monitoring_metrics(
    engine: Engine,
    monitoring_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.volume_monitoring_metrics"
    if monitoring_run_id:
        sql += " WHERE monitoring_run_id = :monitoring_run_id"
        params["monitoring_run_id"] = monitoring_run_id
    sql += " ORDER BY severity_band DESC, volume_type, window_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read volume monitoring: {exc}") from exc


def read_dashboard_backtesting_metrics(
    engine: Engine,
    monitoring_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.backtesting_metrics"
    if monitoring_run_id:
        sql += " WHERE monitoring_run_id = :monitoring_run_id"
        params["monitoring_run_id"] = monitoring_run_id
    sql += " ORDER BY window_name, metric_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read backtesting metrics: {exc}") from exc


def read_dashboard_explainability_runs(
    engine: Engine,
    explanation_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.explainability_runs"
    if explanation_version:
        sql += " WHERE explanation_version = :explanation_version"
        params["explanation_version"] = explanation_version
    sql += " ORDER BY created_at DESC NULLS LAST, explanation_run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read explainability runs: {exc}") from exc


def read_dashboard_global_feature_importance(
    engine: Engine,
    explanation_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.global_feature_importance"
    if explanation_run_id:
        sql += " WHERE explanation_run_id = :explanation_run_id"
        params["explanation_run_id"] = explanation_run_id
    sql += " ORDER BY importance_rank ASC NULLS LAST, feature_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read global feature importance: {exc}") from exc


def read_dashboard_score_decomposition(
    engine: Engine,
    explanation_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.score_decomposition"
    if explanation_run_id:
        sql += " WHERE explanation_run_id = :explanation_run_id"
        params["explanation_run_id"] = explanation_run_id
    sql += " ORDER BY entity_id, contribution_rank ASC NULLS LAST, component_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read score decomposition: {exc}") from exc


def read_dashboard_reason_contributions(
    engine: Engine,
    explanation_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.reason_contributions"
    if explanation_run_id:
        sql += " WHERE explanation_run_id = :explanation_run_id"
        params["explanation_run_id"] = explanation_run_id
    sql += " ORDER BY entity_id, reason_rank ASC NULLS LAST, reason_type, reason_name"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read reason contributions: {exc}") from exc


def read_dashboard_model_cards(
    engine: Engine,
    explanation_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.model_cards"
    if explanation_run_id:
        sql += " WHERE explanation_run_id = :explanation_run_id"
        params["explanation_run_id"] = explanation_run_id
    sql += " ORDER BY created_at DESC NULLS LAST, explanation_run_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise DashboardDataError(f"Failed to read model cards: {exc}") from exc


def read_dashboard_model_metric_bundle(
    engine: Engine,
    config: DashboardConfig | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    resolved = config or DashboardConfig()
    score_limit = limit if limit is not None else resolved.model_metrics.default_score_limit
    model_limit = resolved.model_metrics.default_model_metric_limit
    return {
        "model_runs": read_dashboard_model_runs(engine, limit=model_limit),
        "account_anomaly_scores": read_dashboard_account_anomaly_scores(engine, limit=score_limit),
        "account_risk_scores": read_dashboard_account_risk_scores(engine, limit=score_limit),
        "case_risk_scores": read_dashboard_case_risk_scores(engine, limit=score_limit),
        "supervised_model_scores": read_dashboard_supervised_model_scores(
            engine,
            limit=score_limit,
        ),
        "supervised_model_runs": read_dashboard_supervised_model_runs(
            engine,
            limit=model_limit,
        ),
        "model_comparison_runs": read_dashboard_model_comparison_runs(
            engine,
            limit=model_limit,
        ),
        "model_comparison_metrics": read_dashboard_model_comparison_metrics(
            engine,
            limit=score_limit,
        ),
        "threshold_recommendations": read_dashboard_threshold_recommendations(
            engine,
            limit=score_limit,
        ),
        "champion_challenger_results": read_dashboard_champion_challenger_results(
            engine,
            limit=score_limit,
        ),
        "monitoring_runs": read_dashboard_monitoring_runs(engine, limit=model_limit),
        "drift_metrics": read_dashboard_drift_metrics(engine, limit=score_limit),
        "volume_monitoring_metrics": read_dashboard_volume_monitoring_metrics(
            engine,
            limit=score_limit,
        ),
        "backtesting_metrics": read_dashboard_backtesting_metrics(
            engine,
            limit=score_limit,
        ),
        "explainability_runs": read_dashboard_explainability_runs(
            engine,
            limit=model_limit,
        ),
        "global_feature_importance": read_dashboard_global_feature_importance(
            engine,
            limit=score_limit,
        ),
        "score_decomposition": read_dashboard_score_decomposition(
            engine,
            limit=score_limit,
        ),
        "reason_contributions": read_dashboard_reason_contributions(
            engine,
            limit=score_limit,
        ),
        "model_cards": read_dashboard_model_cards(engine, limit=model_limit),
    }
