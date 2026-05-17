"""Readback utilities for persisted case evidence packs."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CaseEvidencePersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        raise CaseEvidencePersistenceError("limit must be non-negative")
    return int(limit)


def read_case_evidence_packs(
    engine: Engine,
    case_id: str | None = None,
    evidence_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if case_id:
        clauses.append("case_id = :case_id")
        params["case_id"] = case_id
    if evidence_version:
        clauses.append("evidence_version = :evidence_version")
        params["evidence_version"] = evidence_version
    sql = "SELECT * FROM aml.case_evidence_packs"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY case_id, evidence_version"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to read case evidence packs: {exc}") from exc


def read_case_explanations(
    engine: Engine,
    case_id: str | None = None,
    explanation_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    safe_limit = _validate_limit(limit)
    clauses: list[str] = []
    params: dict[str, object] = {}
    if case_id:
        clauses.append("case_id = :case_id")
        params["case_id"] = case_id
    if explanation_version:
        clauses.append("explanation_version = :explanation_version")
        params["explanation_version"] = explanation_version
    sql = "SELECT * FROM aml.case_explanations"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY case_id, explanation_version"
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    try:
        return pd.read_sql_query(text(sql), engine, params=params or None)
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to read case explanations: {exc}") from exc


def read_case_evidence_detail(engine: Engine, case_id: str) -> dict[str, pd.DataFrame]:
    if not case_id.strip():
        raise CaseEvidencePersistenceError("case_id is required")
    return {
        "evidence_packs": read_case_evidence_packs(engine, case_id=case_id),
        "explanations": read_case_explanations(engine, case_id=case_id),
    }


def read_case_evidence_summary(engine: Engine) -> dict[str, object]:
    sql = """
        SELECT
            (SELECT COUNT(*) FROM aml.case_evidence_packs) AS evidence_pack_count,
            (SELECT COUNT(*) FROM aml.case_explanations) AS explanation_count,
            (
                SELECT COUNT(DISTINCT case_id)
                FROM (
                    SELECT case_id FROM aml.case_evidence_packs
                    UNION
                    SELECT case_id FROM aml.case_explanations
                ) AS case_ids
            ) AS unique_case_count,
            (SELECT MAX(created_at) FROM aml.case_evidence_packs) AS max_evidence_created_at,
            (SELECT MAX(created_at) FROM aml.case_explanations) AS max_explanation_created_at
    """
    version_sql = """
        SELECT evidence_version, COUNT(*) AS row_count
        FROM aml.case_evidence_packs
        GROUP BY evidence_version
        ORDER BY evidence_version
    """
    explanation_sql = """
        SELECT explanation_version, COUNT(*) AS row_count
        FROM aml.case_explanations
        GROUP BY explanation_version
        ORDER BY explanation_version
    """
    try:
        summary = pd.read_sql_query(text(sql), engine)
        evidence_versions = pd.read_sql_query(text(version_sql), engine)
        explanation_versions = pd.read_sql_query(text(explanation_sql), engine)
        row = summary.iloc[0].to_dict() if not summary.empty else {}
        return {
            "evidence_pack_count": int(row.get("evidence_pack_count") or 0),
            "explanation_count": int(row.get("explanation_count") or 0),
            "unique_case_count": int(row.get("unique_case_count") or 0),
            "evidence_version_counts": {
                str(item["evidence_version"]): int(item["row_count"])
                for item in evidence_versions.to_dict(orient="records")
            },
            "explanation_version_counts": {
                str(item["explanation_version"]): int(item["row_count"])
                for item in explanation_versions.to_dict(orient="records")
            },
            "max_created_at": str(
                max(
                    row.get("max_evidence_created_at") or "",
                    row.get("max_explanation_created_at") or "",
                )
            ),
        }
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to read case evidence summary: {exc}") from exc
