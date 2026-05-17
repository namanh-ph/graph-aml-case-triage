"""Readback utilities for persisted release readiness outputs."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.release.exceptions import ReleasePersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or limit <= 0:
        raise ReleasePersistenceError("limit must be a positive integer")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine, params=cast(Any, params or {}))
    except Exception as exc:
        raise ReleasePersistenceError(f"release readback failed: {exc}") from exc


def _limit(sql: str, params: dict[str, object], limit: int | None) -> str:
    validated = _validate_limit(limit)
    if validated is not None:
        params["limit"] = validated
        return f"{sql} LIMIT :limit"
    return sql


def read_release_readiness_runs(
    engine: Engine,
    release_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.release_readiness_runs WHERE 1=1"
    if release_version:
        sql += " AND release_version = :release_version"
        params["release_version"] = release_version
    sql += " ORDER BY created_at DESC, release_run_id"
    return _read(engine, _limit(sql, params, limit), params)


def read_release_repository_checks(
    engine: Engine,
    release_run_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.release_repository_checks WHERE 1=1"
    if release_run_id:
        sql += " AND release_run_id = :release_run_id"
        params["release_run_id"] = release_run_id
    if status:
        sql += " AND status = :status"
        params["status"] = status
    sql += " ORDER BY check_name, item_type, item_name"
    return _read(engine, _limit(sql, params, limit), params)


def read_release_documentation_checks(
    engine: Engine,
    release_run_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.release_documentation_checks WHERE 1=1"
    if release_run_id:
        sql += " AND release_run_id = :release_run_id"
        params["release_run_id"] = release_run_id
    if status:
        sql += " AND status = :status"
        params["status"] = status
    sql += " ORDER BY document_path, check_name, required_section"
    return _read(engine, _limit(sql, params, limit), params)


def read_release_artefact_checks(
    engine: Engine,
    release_run_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.release_artefact_checks WHERE 1=1"
    if release_run_id:
        sql += " AND release_run_id = :release_run_id"
        params["release_run_id"] = release_run_id
    if status:
        sql += " AND status = :status"
        params["status"] = status
    sql += " ORDER BY required DESC, artefact_name"
    return _read(engine, _limit(sql, params, limit), params)


def read_release_evidence_index(
    engine: Engine,
    release_run_id: str | None = None,
    evidence_type: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.release_evidence_index WHERE 1=1"
    if release_run_id:
        sql += " AND release_run_id = :release_run_id"
        params["release_run_id"] = release_run_id
    if evidence_type:
        sql += " AND evidence_type = :evidence_type"
        params["evidence_type"] = evidence_type
    sql += " ORDER BY evidence_type, evidence_name"
    return _read(engine, _limit(sql, params, limit), params)


def read_release_portfolio_pack(
    engine: Engine,
    release_run_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    sql = "SELECT * FROM governance.release_portfolio_pack WHERE 1=1"
    if release_run_id:
        sql += " AND release_run_id = :release_run_id"
        params["release_run_id"] = release_run_id
    sql += " ORDER BY created_at DESC, release_run_id"
    return _read(engine, _limit(sql, params, limit), params)


def read_release_readiness_summary(engine: Engine) -> dict[str, object]:
    """Read compact release readiness summary."""

    runs = read_release_readiness_runs(engine, limit=1)
    latest_run_id = str(runs.iloc[0]["release_run_id"]) if not runs.empty else None
    latest_version = str(runs.iloc[0]["release_version"]) if not runs.empty else None
    artefacts = (
        read_release_artefact_checks(engine, latest_run_id, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    evidence = (
        read_release_evidence_index(engine, latest_run_id, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    portfolios = (
        read_release_portfolio_pack(engine, latest_run_id, limit=100000)
        if latest_run_id
        else pd.DataFrame()
    )
    return {
        "release_run_count": int(len(read_release_readiness_runs(engine, limit=100000))),
        "latest_release_version": latest_version,
        "latest_release_run_id": latest_run_id,
        "failed_check_count": int(runs.iloc[0]["failed_check_count"]) if not runs.empty else 0,
        "warning_check_count": int(runs.iloc[0]["warning_check_count"]) if not runs.empty else 0,
        "validation_artefact_count": int(len(artefacts)),
        "evidence_item_count": int(len(evidence)),
        "portfolio_pack_count": int(len(portfolios)),
    }
