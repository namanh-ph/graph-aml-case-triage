"""Persistence utilities for release readiness outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.exceptions import ReleasePersistenceError
from graph_aml.release.validation import ReleaseReadinessResult


@dataclass(frozen=True)
class ReleasePersistenceConfig:
    release_name: str = "aml_portfolio_release"
    release_version: str = "portfolio_release_v1"
    batch_size: int = 1000
    write_audit: bool = True


@dataclass(frozen=True)
class ReleasePersistenceResult:
    release_run_id: str | None = None
    release_run_persisted: bool = False
    repository_checks_persisted: int = 0
    documentation_checks_persisted: int = 0
    artefact_checks_persisted: int = 0
    evidence_index_persisted: int = 0
    portfolio_pack_persisted: bool = False
    release_name: str | None = None
    release_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_release_persistence_config(config: ReleasePersistenceConfig) -> None:
    if not config.release_name.strip() or not config.release_version.strip():
        raise ReleasePersistenceError("release name and version must be non-empty")
    if config.batch_size <= 0:
        raise ReleasePersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise ReleasePersistenceError("write_audit must be boolean")


def build_release_readiness_run_insert_sql() -> str:
    return """
    INSERT INTO governance.release_readiness_runs (
        release_run_id, release_name, release_version, repository_check_count,
        documentation_check_count, artefact_check_count, failed_check_count,
        warning_check_count, validation_artefact_count, evidence_item_count,
        summary, metadata
    ) VALUES (
        :release_run_id, :release_name, :release_version, :repository_check_count,
        :documentation_check_count, :artefact_check_count, :failed_check_count,
        :warning_check_count, :validation_artefact_count, :evidence_item_count,
        CAST(:summary AS jsonb), CAST(:metadata AS jsonb)
    )
    ON CONFLICT (release_run_id) DO NOTHING
    """


def build_release_repository_check_insert_sql() -> str:
    return """
    INSERT INTO governance.release_repository_checks (
        release_run_id, check_name, item_type, item_name, status, severity, details, metadata
    ) VALUES (
        :release_run_id, :check_name, :item_type, :item_name, :status, :severity,
        CAST(:details AS jsonb), CAST(:metadata AS jsonb)
    )
    """


def build_release_documentation_check_insert_sql() -> str:
    return """
    INSERT INTO governance.release_documentation_checks (
        release_run_id, document_path, check_name, required_section, status,
        severity, details, metadata
    ) VALUES (
        :release_run_id, :document_path, :check_name, :required_section, :status,
        :severity, CAST(:details AS jsonb), CAST(:metadata AS jsonb)
    )
    """


def build_release_artefact_check_insert_sql() -> str:
    return """
    INSERT INTO governance.release_artefact_checks (
        release_run_id, artefact_name, relative_path, artefact_type, required,
        status, size_bytes, modified_at, details, metadata
    ) VALUES (
        :release_run_id, :artefact_name, :relative_path, :artefact_type, :required,
        :status, :size_bytes, :modified_at, CAST(:details AS jsonb), CAST(:metadata AS jsonb)
    )
    """


def build_release_evidence_index_insert_sql() -> str:
    return """
    INSERT INTO governance.release_evidence_index (
        release_run_id, evidence_name, evidence_type, relative_path, status, details, metadata
    ) VALUES (
        :release_run_id, :evidence_name, :evidence_type, :relative_path, :status,
        CAST(:details AS jsonb), CAST(:metadata AS jsonb)
    )
    """


def build_release_portfolio_pack_upsert_sql() -> str:
    return """
    INSERT INTO governance.release_portfolio_pack (
        release_run_id, portfolio_summary_md, architecture_summary_md,
        dashboard_walkthrough_md, command_transcript_template_md,
        demo_validation_checklist_md, validation_index, evidence_index, summary, metadata
    ) VALUES (
        :release_run_id, :portfolio_summary_md, :architecture_summary_md,
        :dashboard_walkthrough_md, :command_transcript_template_md,
        :demo_validation_checklist_md, CAST(:validation_index AS jsonb),
        CAST(:evidence_index AS jsonb), CAST(:summary AS jsonb), CAST(:metadata AS jsonb)
    )
    ON CONFLICT (release_run_id) DO UPDATE SET
        portfolio_summary_md = EXCLUDED.portfolio_summary_md,
        architecture_summary_md = EXCLUDED.architecture_summary_md,
        dashboard_walkthrough_md = EXCLUDED.dashboard_walkthrough_md,
        command_transcript_template_md = EXCLUDED.command_transcript_template_md,
        demo_validation_checklist_md = EXCLUDED.demo_validation_checklist_md,
        validation_index = EXCLUDED.validation_index,
        evidence_index = EXCLUDED.evidence_index,
        summary = EXCLUDED.summary,
        metadata = EXCLUDED.metadata
    """


def _json_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    prepared = frame.astype(object).where(pd.notna(frame), cast(Any, None)).copy()
    for column in columns:
        if column in prepared.columns:
            prepared[column] = [
                json.dumps(value if value is not None else {}, sort_keys=True, default=str)
                for value in prepared[column].tolist()
            ]
    return prepared


def _records(frame: pd.DataFrame, json_columns: tuple[str, ...]) -> list[dict[str, object]]:
    if frame.empty:
        return []
    return cast(list[dict[str, object]], _json_columns(frame, json_columns).to_dict("records"))


def _summary_int(summary: dict[str, object], key: str) -> int:
    value = summary.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        return int(value)
    return 0


def persist_release_readiness_result(
    engine: Engine,
    result: ReleaseReadinessResult,
    config: ReleaseReadinessConfig | None = None,
    persistence_config: ReleasePersistenceConfig | None = None,
) -> ReleasePersistenceResult:
    """Persist release readiness result rows."""

    resolved = config or ReleaseReadinessConfig()
    persistence = persistence_config or ReleasePersistenceConfig(
        release_name=resolved.release_name,
        release_version=resolved.release_version,
        write_audit=resolved.persistence.write_audit,
    )
    validate_release_persistence_config(persistence)
    run_row = {
        "release_run_id": result.release_run_id,
        "release_name": resolved.release_name,
        "release_version": resolved.release_version,
        "repository_check_count": len(result.repository_checks),
        "documentation_check_count": len(result.documentation_checks),
        "artefact_check_count": len(result.artefact_checks),
        "failed_check_count": _summary_int(result.summary, "failed_check_count"),
        "warning_check_count": _summary_int(result.summary, "warning_check_count"),
        "validation_artefact_count": len(result.validation_index),
        "evidence_item_count": len(result.evidence_index),
        "summary": json.dumps(result.summary, sort_keys=True, default=str),
        "metadata": json.dumps(result.metadata, sort_keys=True, default=str),
    }
    pack = result.portfolio_pack
    pack_row = {
        "release_run_id": result.release_run_id,
        "portfolio_summary_md": pack.portfolio_summary_md,
        "architecture_summary_md": pack.architecture_summary_md,
        "dashboard_walkthrough_md": pack.dashboard_walkthrough_md,
        "command_transcript_template_md": pack.command_transcript_template_md,
        "demo_validation_checklist_md": pack.demo_validation_checklist_md,
        "validation_index": pack.validation_index.astype(object).where(
            pd.notna(pack.validation_index), cast(Any, None)
        ).to_json(orient="records"),
        "evidence_index": pack.evidence_index.astype(object).where(
            pd.notna(pack.evidence_index), cast(Any, None)
        ).to_json(orient="records"),
        "summary": json.dumps(pack.summary, sort_keys=True, default=str),
        "metadata": json.dumps(pack.metadata, sort_keys=True, default=str),
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(build_release_readiness_run_insert_sql()), run_row)
            for frame, sql in (
                (result.repository_checks, build_release_repository_check_insert_sql()),
                (result.documentation_checks, build_release_documentation_check_insert_sql()),
                (result.artefact_checks, build_release_artefact_check_insert_sql()),
                (result.evidence_index, build_release_evidence_index_insert_sql()),
            ):
                rows = _records(frame, ("details", "metadata"))
                if rows:
                    connection.execute(text(sql), rows)
            connection.execute(text(build_release_portfolio_pack_upsert_sql()), pack_row)
        persisted = ReleasePersistenceResult(
            release_run_id=result.release_run_id,
            release_run_persisted=True,
            repository_checks_persisted=len(result.repository_checks),
            documentation_checks_persisted=len(result.documentation_checks),
            artefact_checks_persisted=len(result.artefact_checks),
            evidence_index_persisted=len(result.evidence_index),
            portfolio_pack_persisted=True,
            release_name=resolved.release_name,
            release_version=resolved.release_version,
            persisted=True,
            metadata=result.metadata,
            summary=result.summary,
        )
        if persistence.write_audit:
            write_release_readiness_audit_event(engine, persisted, run_id=result.release_run_id)
        return persisted
    except ReleasePersistenceError:
        raise
    except Exception as exc:
        raise ReleasePersistenceError(f"failed to persist release readiness: {exc}") from exc


def write_release_readiness_audit_event(
    engine: Engine,
    result: ReleasePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write a release readiness audit event."""

    sql = """
    INSERT INTO governance.audit_events (
        event_type, component, action, status, run_id, details
    ) VALUES (
        :event_type, :component, :action, :status, :run_id, CAST(:details AS jsonb)
    )
    """
    details = {
        "release_run_id": result.release_run_id,
        "repository_checks_persisted": result.repository_checks_persisted,
        "documentation_checks_persisted": result.documentation_checks_persisted,
        "artefact_checks_persisted": result.artefact_checks_persisted,
        "evidence_index_persisted": result.evidence_index_persisted,
        "portfolio_pack_persisted": result.portfolio_pack_persisted,
        "release_name": result.release_name,
        "release_version": result.release_version,
        "summary": result.summary,
        "metadata": result.metadata,
    }
    try:
        with engine.begin() as connection:
            connection.execute(
                text(sql),
                {
                    "event_type": "release_readiness",
                    "component": "release",
                    "action": "persist_release_readiness_result",
                    "status": status,
                    "run_id": run_id or result.release_run_id,
                    "details": json.dumps(details, sort_keys=True, default=str),
                },
            )
    except Exception as exc:
        raise ReleasePersistenceError(f"failed to write release audit event: {exc}") from exc
