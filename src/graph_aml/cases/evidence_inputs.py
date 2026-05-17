"""PostgreSQL readers for case evidence pack inputs."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.evidence_config import CaseEvidenceConfig
from graph_aml.cases.exceptions import CaseEvidenceInputError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CaseEvidenceInputError("limit must be non-negative")
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


def _read_query(engine: Engine, sql: str, params: dict[str, object], label: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseEvidenceInputError(f"Failed to read {label}: {exc}") from exc


def read_evidence_cases(
    engine: Engine,
    case_version: str | None = None,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if case_version:
        clauses.append("case_version = :case_version")
        params["case_version"] = case_version
    clause, id_params = _id_filter("case_id", "case_ids", case_ids)
    if clause:
        clauses.append(clause)
        params.update(id_params)
    sql = "SELECT * FROM aml.cases"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY priority_score DESC NULLS LAST, case_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "evidence cases")


def read_evidence_case_alerts(
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
    return _read_query(engine, sql, params, "case-alert links")


def read_evidence_case_entities(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("case_id", "case_ids", case_ids)
    sql = "SELECT * FROM aml.case_entities"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY case_id, entity_type, entity_id"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "case-entity links")


def read_evidence_alerts(
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
    return _read_query(engine, sql, params, "evidence alerts")


def read_evidence_transactions(
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
    return _read_query(engine, sql, params, "evidence transactions")


def read_evidence_account_risk_scores(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.account_risk_scores"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, scored_at DESC NULLS LAST, account_risk_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "account risk scores")


def read_evidence_case_risk_scores(
    engine: Engine,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("case_id", "case_ids", case_ids)
    sql = "SELECT * FROM aml.case_risk_scores"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY case_id, scored_at DESC NULLS LAST, case_risk_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "case risk scores")


def read_evidence_graph_features(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.graph_features"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, computed_at DESC NULLS LAST"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "graph features")


def read_evidence_anomaly_scores(
    engine: Engine,
    account_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clause, params = _id_filter("account_id", "account_ids", account_ids)
    sql = "SELECT * FROM mart.account_anomaly_scores"
    if clause:
        sql += " WHERE " + clause
    sql += " ORDER BY account_id, scored_at DESC NULLS LAST, anomaly_score DESC"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return _read_query(engine, sql, params, "anomaly scores")


def read_case_evidence_inputs(
    engine: Engine,
    config: CaseEvidenceConfig | None = None,
    case_ids: tuple[str, ...] | list[str] | None = None,
    limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read all case evidence inputs from PostgreSQL."""

    _ = CaseEvidenceConfig() if config is None else config
    cases = read_evidence_cases(engine, case_ids=case_ids, limit=limit)
    case_id_values = tuple(cases["case_id"].astype(str).tolist()) if "case_id" in cases else ()
    case_alerts = read_evidence_case_alerts(engine, case_ids=case_id_values, limit=limit)
    case_entities = read_evidence_case_entities(engine, case_ids=case_id_values, limit=limit)
    alert_ids = (
        tuple(case_alerts["alert_id"].dropna().astype(str).tolist())
        if "alert_id" in case_alerts
        else ()
    )
    alerts = read_evidence_alerts(engine, alert_ids=alert_ids, limit=limit)
    from graph_aml.cases.evidence_builders import normalise_evidence_list

    account_ids: set[str] = set()
    for column in ("primary_account_id", "related_accounts"):
        if column in cases:
            for value in cases[column].tolist():
                account_ids.update(normalise_evidence_list(value))
    if "account_id" in alerts:
        account_ids.update(alerts["account_id"].dropna().astype(str).tolist())
    transaction_ids: set[str] = set()
    if "evidence_ids" in alerts:
        for value in alerts["evidence_ids"].tolist():
            transaction_ids.update(normalise_evidence_list(value))
    return {
        "cases": cases,
        "case_alerts": case_alerts,
        "case_entities": case_entities,
        "alerts": alerts,
        "transactions": read_evidence_transactions(
            engine, transaction_ids=tuple(sorted(transaction_ids)), limit=limit
        ),
        "account_risk_scores": read_evidence_account_risk_scores(
            engine, account_ids=tuple(sorted(account_ids)), limit=limit
        ),
        "case_risk_scores": read_evidence_case_risk_scores(
            engine, case_ids=case_id_values, limit=limit
        ),
        "graph_features": read_evidence_graph_features(
            engine, account_ids=tuple(sorted(account_ids)), limit=limit
        ),
        "anomaly_scores": read_evidence_anomaly_scores(
            engine, account_ids=tuple(sorted(account_ids)), limit=limit
        ),
    }
