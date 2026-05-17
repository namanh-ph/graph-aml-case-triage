"""PostgreSQL readers for case-level risk scoring inputs."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CaseRiskInputError
from graph_aml.cases.risk_config import CaseRiskScoringConfig


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CaseRiskInputError("limit must be non-negative")
    return int(limit)


def _id_filter(
    column: str,
    param_name: str,
    values: tuple[str, ...] | list[str] | None,
) -> tuple[str | None, dict[str, object]]:
    if not values:
        return None, {}
    clean = [str(value).strip() for value in values if str(value).strip()]
    if not clean:
        return None, {}
    return f"{column} = ANY(:{param_name})", {param_name: clean}


def read_case_risk_cases(
    engine: Engine,
    case_version: str | None = None,
    min_priority_score: float | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if case_version:
        clauses.append("case_version = :case_version")
        params["case_version"] = case_version
    if min_priority_score is not None:
        if min_priority_score < 0 or min_priority_score > 100:
            raise CaseRiskInputError("min_priority_score must be in [0, 100]")
        clauses.append("COALESCE(priority_score, 0) >= :min_priority_score")
        params["min_priority_score"] = float(min_priority_score)
    sql = "SELECT * FROM aml.cases"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY priority_score DESC, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read case risk cases: {exc}") from exc


def read_case_risk_case_alerts(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("case_id", "case_ids", case_ids)
    sql = "SELECT * FROM aml.case_alerts"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY case_id, alert_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read case-alert links: {exc}") from exc


def read_case_risk_alerts(
    engine: Engine,
    alert_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("alert_id", "alert_ids", alert_ids)
    sql = "SELECT * FROM aml.alerts"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, alert_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read case risk alerts: {exc}") from exc


def read_case_risk_account_scores(
    engine: Engine,
    score_version: str | None = None,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if score_version:
        clauses.append("score_version = :score_version")
        params["score_version"] = score_version
    clause, id_params = _id_filter("account_id", "account_ids", account_ids)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    sql = "SELECT * FROM mart.account_risk_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY account_id, scored_at DESC NULLS LAST, account_risk_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read account risk scores: {exc}") from exc


def read_case_risk_graph_features(
    engine: Engine,
    feature_version: str | None = None,
    graph_build_id: str | None = None,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if feature_version:
        clauses.append("feature_version = :feature_version")
        params["feature_version"] = feature_version
    if graph_build_id:
        clauses.append("graph_build_id = :graph_build_id")
        params["graph_build_id"] = graph_build_id
    clause, id_params = _id_filter("account_id", "account_ids", account_ids)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    sql = "SELECT * FROM mart.graph_features"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY account_id, computed_at DESC NULLS LAST"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read graph features: {exc}") from exc


def read_case_risk_anomaly_scores(
    engine: Engine,
    model_version: str | None = None,
    model_run_id: str | None = None,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    if model_run_id:
        clauses.append("model_run_id = :model_run_id")
        params["model_run_id"] = model_run_id
    clause, id_params = _id_filter("account_id", "account_ids", account_ids)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    sql = "SELECT * FROM mart.account_anomaly_scores"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY account_id, scored_at DESC NULLS LAST, anomaly_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read anomaly scores: {exc}") from exc


def read_case_risk_transactions(
    engine: Engine,
    transaction_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("transaction_id", "transaction_ids", transaction_ids)
    sql = "SELECT * FROM staging.transactions"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY transaction_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseRiskInputError(f"Failed to read evidence transactions: {exc}") from exc


def read_case_risk_inputs(
    engine: Engine,
    config: CaseRiskScoringConfig | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    resolved = CaseRiskScoringConfig() if config is None else config
    cases = read_case_risk_cases(
        engine,
        case_version=resolved.case_version,
        min_priority_score=resolved.thresholds.min_case_priority_score,
        limit=limit,
    )
    case_ids = tuple(cases["case_id"].astype(str).tolist()) if "case_id" in cases.columns else ()
    case_alerts = read_case_risk_case_alerts(engine, case_ids=case_ids, limit=limit)
    alert_ids = (
        tuple(case_alerts["alert_id"].astype(str).tolist())
        if "alert_id" in case_alerts.columns
        else ()
    )
    alerts = read_case_risk_alerts(engine, alert_ids=alert_ids, limit=limit)
    account_ids: set[str] = set()
    if "primary_account_id" in cases.columns:
        account_ids.update(cases["primary_account_id"].dropna().astype(str).tolist())
    if "related_accounts" in cases.columns:
        from graph_aml.cases.risk_components import normalise_case_id_list

        for value in cases["related_accounts"].tolist():
            account_ids.update(normalise_case_id_list(value))
    transaction_ids: set[str] = set()
    if "alert_ids" in cases.columns:
        for value in cases["alert_ids"].tolist():
            transaction_ids.update(normalise_case_id_list(value))
    if "evidence_ids" in alerts.columns:
        from graph_aml.cases.risk_components import normalise_case_id_list

        for value in alerts["evidence_ids"].tolist():
            transaction_ids.update(normalise_case_id_list(value))
    return {
        "cases": cases,
        "case_alerts": case_alerts,
        "alerts": alerts,
        "account_risk_scores": read_case_risk_account_scores(
            engine,
            score_version=resolved.account_risk_score_version,
            account_ids=tuple(sorted(account_ids)),
            limit=limit,
        ),
        "graph_features": read_case_risk_graph_features(
            engine,
            feature_version=resolved.graph_feature_version,
            graph_build_id=resolved.graph_build_id,
            account_ids=tuple(sorted(account_ids)),
            limit=limit,
        ),
        "anomaly_scores": read_case_risk_anomaly_scores(
            engine,
            model_version=resolved.anomaly_model_version,
            model_run_id=resolved.anomaly_model_run_id,
            account_ids=tuple(sorted(account_ids)),
            limit=limit,
        ),
        "transactions": read_case_risk_transactions(
            engine,
            transaction_ids=tuple(sorted(transaction_ids)),
            limit=limit,
        ),
    }
