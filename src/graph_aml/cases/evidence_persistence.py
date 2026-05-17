"""PostgreSQL persistence for case evidence packs and explanations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.evidence_builders import CaseEvidenceBuildResult
from graph_aml.cases.evidence_validation import (
    CASE_EVIDENCE_PERSISTENCE_COLUMNS,
    CASE_EXPLANATION_PERSISTENCE_COLUMNS,
    validate_prepared_case_evidence_frames,
)
from graph_aml.cases.exceptions import CaseEvidencePersistenceError, CaseEvidenceValidationError

DEFAULT_EVIDENCE_VERSION = "case_evidence_v1"
DEFAULT_EXPLANATION_VERSION = "deterministic_explanation_v1"
_EVIDENCE_JSON_COLUMNS = (
    "case_summary",
    "typology_evidence",
    "alert_evidence",
    "transaction_evidence",
    "account_evidence",
    "graph_evidence",
    "risk_driver_evidence",
    "chronology",
    "recommended_review_focus",
    "evidence_quality",
)
_EXPLANATION_JSON_COLUMNS = ("explanation_bullets",)


@dataclass(frozen=True)
class CaseEvidencePersistenceConfig:
    evidence_version: str = DEFAULT_EVIDENCE_VERSION
    explanation_version: str = DEFAULT_EXPLANATION_VERSION
    batch_size: int = 1000
    write_audit: bool = True

    def __post_init__(self) -> None:
        validate_case_evidence_persistence_config(self)


@dataclass(frozen=True)
class CaseEvidencePersistenceResult:
    evidence_packs_prepared: int = 0
    evidence_packs_persisted: int = 0
    explanations_prepared: int = 0
    explanations_persisted: int = 0
    unique_case_count: int = 0
    evidence_version: str | None = None
    explanation_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_case_evidence_persistence_config(config: CaseEvidencePersistenceConfig) -> None:
    if not isinstance(config, CaseEvidencePersistenceConfig):
        raise CaseEvidencePersistenceError("config must be CaseEvidencePersistenceConfig")
    if not config.evidence_version.strip():
        raise CaseEvidencePersistenceError("evidence_version must be non-empty")
    if not config.explanation_version.strip():
        raise CaseEvidencePersistenceError("explanation_version must be non-empty")
    if config.batch_size <= 0:
        raise CaseEvidencePersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise CaseEvidencePersistenceError("write_audit must be boolean")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return cast(Any, value).item()
        except (AttributeError, ValueError):
            return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _to_db_value(value: object) -> object:
    if isinstance(value, dict | list | tuple):
        return json.dumps(_json_safe(value), sort_keys=True, default=str)
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        try:
            return cast(Any, value).item()
        except (AttributeError, ValueError):
            return str(value)
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {str(column): _to_db_value(value) for column, value in row.items()}
        for row in frame.astype(object).to_dict(orient="records")
    ]


def prepare_case_evidence_for_persistence(
    result: CaseEvidenceBuildResult,
    config: CaseEvidencePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> dict[str, pd.DataFrame]:
    """Prepare evidence packs and explanations for database persistence."""

    resolved = CaseEvidencePersistenceConfig() if config is None else config
    try:
        evidence = result.evidence_packs.copy(deep=True)
        explanations = result.explanations.copy(deep=True)
        now = _utc_now()
        if evidence.empty:
            evidence = pd.DataFrame(columns=CASE_EVIDENCE_PERSISTENCE_COLUMNS)
        else:
            evidence["evidence_version"] = resolved.evidence_version
            evidence["updated_at"] = now
            evidence = evidence.drop_duplicates(["case_id", "evidence_version"], keep="last")
            evidence = evidence.loc[:, CASE_EVIDENCE_PERSISTENCE_COLUMNS]
        if explanations.empty:
            explanations = pd.DataFrame(columns=CASE_EXPLANATION_PERSISTENCE_COLUMNS)
        else:
            explanations["explanation_version"] = resolved.explanation_version
            explanations["updated_at"] = now
            explanations = explanations.drop_duplicates(
                ["case_id", "explanation_version"], keep="last"
            )
            explanations = explanations.loc[:, CASE_EXPLANATION_PERSISTENCE_COLUMNS]
        prepared = {"evidence_packs": evidence, "explanations": explanations}
        validate_prepared_case_evidence_frames(prepared)
        if extra_metadata:
            # Metadata is persisted through audit, keeping table payloads focused.
            _ = _json_safe(extra_metadata)
        return prepared
    except CaseEvidenceValidationError as exc:
        raise CaseEvidencePersistenceError(str(exc)) from exc
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to prepare case evidence: {exc}") from exc


def build_case_evidence_pack_upsert_sql() -> str:
    columns = ", ".join(CASE_EVIDENCE_PERSISTENCE_COLUMNS)
    placeholders = ", ".join(
        f"CAST(:{column} AS JSONB)" if column in _EVIDENCE_JSON_COLUMNS else f":{column}"
        for column in CASE_EVIDENCE_PERSISTENCE_COLUMNS
    )
    update_columns = [
        column
        for column in CASE_EVIDENCE_PERSISTENCE_COLUMNS
        if column not in {"case_id", "evidence_version", "created_at"}
    ]
    updates = ",\n            ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return f"""
        INSERT INTO aml.case_evidence_packs ({columns})
        VALUES ({placeholders})
        ON CONFLICT (case_id, evidence_version) DO UPDATE SET
            {updates},
            updated_at = CURRENT_TIMESTAMP
    """


def build_case_explanation_upsert_sql() -> str:
    columns = ", ".join(CASE_EXPLANATION_PERSISTENCE_COLUMNS)
    placeholders = ", ".join(
        f"CAST(:{column} AS JSONB)" if column in _EXPLANATION_JSON_COLUMNS else f":{column}"
        for column in CASE_EXPLANATION_PERSISTENCE_COLUMNS
    )
    update_columns = [
        column
        for column in CASE_EXPLANATION_PERSISTENCE_COLUMNS
        if column not in {"case_id", "explanation_version", "created_at"}
    ]
    updates = ",\n            ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return f"""
        INSERT INTO aml.case_explanations ({columns})
        VALUES ({placeholders})
        ON CONFLICT (case_id, explanation_version) DO UPDATE SET
            {updates},
            updated_at = CURRENT_TIMESTAMP
    """


def _upsert_frame(engine: Engine, frame: pd.DataFrame, sql: str, batch_size: int) -> int:
    if batch_size <= 0:
        raise CaseEvidencePersistenceError("batch_size must be positive")
    if frame.empty:
        return 0
    rows = _records(frame)
    statement = text(sql)
    with engine.begin() as connection:
        for start in range(0, len(rows), batch_size):
            connection.execute(statement, rows[start : start + batch_size])
    return len(rows)


def upsert_case_evidence_packs(
    engine: Engine,
    evidence_packs: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    try:
        if evidence_packs.empty:
            return 0
        return _upsert_frame(
            engine, evidence_packs, build_case_evidence_pack_upsert_sql(), batch_size
        )
    except Exception as exc:
        if isinstance(exc, CaseEvidencePersistenceError):
            raise
        raise CaseEvidencePersistenceError(f"Failed to upsert evidence packs: {exc}") from exc


def upsert_case_explanations(
    engine: Engine,
    explanations: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    try:
        if explanations.empty:
            return 0
        return _upsert_frame(engine, explanations, build_case_explanation_upsert_sql(), batch_size)
    except Exception as exc:
        if isinstance(exc, CaseEvidencePersistenceError):
            raise
        raise CaseEvidencePersistenceError(f"Failed to upsert case explanations: {exc}") from exc


def persist_case_evidence(
    engine: Engine,
    result: CaseEvidenceBuildResult,
    config: CaseEvidencePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> CaseEvidencePersistenceResult:
    resolved = CaseEvidencePersistenceConfig() if config is None else config
    try:
        prepared = prepare_case_evidence_for_persistence(result, resolved, extra_metadata)
        evidence_rows = upsert_case_evidence_packs(
            engine, prepared["evidence_packs"], resolved.batch_size
        )
        explanation_rows = upsert_case_explanations(
            engine, prepared["explanations"], resolved.batch_size
        )
        unique_cases = set(
            prepared["evidence_packs"].get("case_id", pd.Series(dtype=str)).astype(str)
        )
        unique_cases.update(
            prepared["explanations"].get("case_id", pd.Series(dtype=str)).astype(str)
        )
        persistence_result = CaseEvidencePersistenceResult(
            evidence_packs_prepared=len(prepared["evidence_packs"]),
            evidence_packs_persisted=evidence_rows,
            explanations_prepared=len(prepared["explanations"]),
            explanations_persisted=explanation_rows,
            unique_case_count=len(unique_cases),
            evidence_version=resolved.evidence_version,
            explanation_version=resolved.explanation_version,
            persisted=(evidence_rows + explanation_rows) > 0,
            metadata={
                "extra_metadata": _json_safe(extra_metadata or {}),
                "build_metadata": result.metadata,
            },
            summary={
                "evidence_packs_persisted": int(evidence_rows),
                "explanations_persisted": int(explanation_rows),
            },
        )
        if resolved.write_audit:
            write_case_evidence_audit_event(engine, persistence_result, status="success")
        return persistence_result
    except CaseEvidencePersistenceError:
        raise
    except Exception as exc:
        raise CaseEvidencePersistenceError(f"Failed to persist case evidence: {exc}") from exc


def write_case_evidence_audit_event(
    engine: Engine,
    result: CaseEvidencePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    details = {
        "evidence_packs_prepared": int(result.evidence_packs_prepared),
        "evidence_packs_persisted": int(result.evidence_packs_persisted),
        "explanations_prepared": int(result.explanations_prepared),
        "explanations_persisted": int(result.explanations_persisted),
        "unique_case_count": int(result.unique_case_count),
        "evidence_version": result.evidence_version,
        "explanation_version": result.explanation_version,
        "summary": result.summary,
        "metadata": result.metadata,
    }
    statement = text(
        """
        INSERT INTO governance.audit_events (
            event_type, component, run_id, pipeline_stage, entity_type, entity_id,
            action, status, details
        )
        VALUES (
            :event_type, :component, :run_id, :pipeline_stage, :entity_type, :entity_id,
            :action, :status, CAST(:details AS JSONB)
        )
        """
    )
    params = {
        "event_type": "case_evidence_generation",
        "component": "cases",
        "run_id": run_id,
        "pipeline_stage": "case_evidence",
        "entity_type": "case",
        "entity_id": result.evidence_version,
        "action": "persist_case_evidence_packs",
        "status": status,
        "details": json.dumps(details, sort_keys=True, default=str),
    }
    try:
        with engine.begin() as connection:
            connection.execute(statement, params)
    except Exception as exc:
        raise CaseEvidencePersistenceError(
            f"Failed to write case evidence audit event: {exc}"
        ) from exc
