"""Release readiness workflow and validation helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from graph_aml.release.artefact_checks import (
    ARTEFACT_CHECK_COLUMNS,
    build_release_validation_index,
    run_artefact_checks,
)
from graph_aml.release.config import ReleaseReadinessConfig
from graph_aml.release.documentation_checks import (
    DOCUMENTATION_CHECK_COLUMNS,
    run_documentation_checks,
)
from graph_aml.release.exceptions import ReleaseReadinessError, ReleaseValidationError
from graph_aml.release.portfolio_pack import ReleasePortfolioPack, build_release_portfolio_pack
from graph_aml.release.repository_checks import REPOSITORY_CHECK_COLUMNS, run_repository_checks

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from graph_aml.release.persistence import ReleasePersistenceConfig, ReleasePersistenceResult


@dataclass(frozen=True)
class ReleaseReadinessResult:
    release_run_id: str
    repository_checks: pd.DataFrame
    documentation_checks: pd.DataFrame
    artefact_checks: pd.DataFrame
    validation_index: pd.DataFrame
    evidence_index: pd.DataFrame
    portfolio_pack: ReleasePortfolioPack
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def build_release_run_id(
    config: ReleaseReadinessConfig | None = None,
    generated_at: pd.Timestamp | None = None,
) -> str:
    """Build a deterministic release run ID for a timestamp and config."""

    resolved = config or ReleaseReadinessConfig()
    timestamp = (generated_at or pd.Timestamp.utcnow()).isoformat()
    digest = hashlib.sha256(
        f"{resolved.release_name}|{resolved.release_version}|{timestamp}".encode()
    ).hexdigest()[:12]
    return f"{resolved.release_version}_{pd.Timestamp(timestamp).strftime('%Y%m%d%H%M%S')}_{digest}"


def _missing_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> set[str]:
    return set(columns).difference(frame.columns)


def validate_release_readiness_result(
    result: ReleaseReadinessResult,
) -> None:
    """Validate required release output frames and run IDs."""

    if not result.release_run_id:
        raise ReleaseValidationError("release_run_id must be non-empty")
    for frame, columns in (
        (result.repository_checks, REPOSITORY_CHECK_COLUMNS),
        (result.documentation_checks, DOCUMENTATION_CHECK_COLUMNS),
        (result.artefact_checks, ARTEFACT_CHECK_COLUMNS),
        (result.validation_index, ARTEFACT_CHECK_COLUMNS),
    ):
        missing = _missing_columns(frame, columns)
        if missing:
            raise ReleaseValidationError(f"release frame missing columns: {sorted(missing)}")
    if result.evidence_index.empty and result.portfolio_pack.evidence_index.empty:
        raise ReleaseValidationError("release evidence index must not be empty")


def build_release_quality_summary(result: ReleaseReadinessResult) -> dict[str, object]:
    """Build JSON-serialisable release quality summary."""

    frames = (result.repository_checks, result.documentation_checks, result.artefact_checks)
    failed = sum(
        int((frame.get("status", pd.Series(dtype=str)).astype(str) == "fail").sum())
        for frame in frames
    )
    warnings = sum(
        int((frame.get("status", pd.Series(dtype=str)).astype(str) == "warning").sum())
        for frame in frames
    )
    return {
        "release_run_id": result.release_run_id,
        "release_version": result.metadata.get("release_version"),
        "repository_check_count": int(len(result.repository_checks)),
        "documentation_check_count": int(len(result.documentation_checks)),
        "artefact_check_count": int(len(result.artefact_checks)),
        "failed_check_count": int(failed),
        "warning_check_count": int(warnings),
        "validation_artefact_count": int(len(result.validation_index)),
        "evidence_item_count": int(len(result.evidence_index)),
    }


def run_release_readiness_from_inputs(
    inputs: dict[str, object],
    config: ReleaseReadinessConfig | None = None,
) -> ReleaseReadinessResult:
    """Build release readiness outputs from read-only inputs and local files."""

    if not isinstance(inputs, dict):
        raise ReleaseValidationError("release inputs must be a mapping")
    resolved = config or ReleaseReadinessConfig()
    generated_at = pd.Timestamp.utcnow()
    run_id = build_release_run_id(resolved, generated_at)
    try:
        repository = run_repository_checks(resolved, run_id)
        documentation = run_documentation_checks(resolved, run_id)
        artefacts = run_artefact_checks(resolved, run_id)
        validation_index = build_release_validation_index(resolved, run_id)
        pack = build_release_portfolio_pack(inputs, validation_index, resolved, run_id)
        metadata: dict[str, object] = {
            "release_name": resolved.release_name,
            "release_version": resolved.release_version,
            "generated_at": generated_at.isoformat(),
            "input_availability": {
                str(key): value is not None for key, value in inputs.items()
            },
        }
        result = ReleaseReadinessResult(
            release_run_id=run_id,
            repository_checks=repository,
            documentation_checks=documentation,
            artefact_checks=artefacts,
            validation_index=validation_index,
            evidence_index=pack.evidence_index,
            portfolio_pack=pack,
            summary={},
            metadata=metadata,
        )
        summary = {
            **build_release_quality_summary(result),
            "generated_timestamp": generated_at.isoformat(),
        }
        result = ReleaseReadinessResult(
            release_run_id=result.release_run_id,
            repository_checks=result.repository_checks,
            documentation_checks=result.documentation_checks,
            artefact_checks=result.artefact_checks,
            validation_index=result.validation_index,
            evidence_index=result.evidence_index,
            portfolio_pack=result.portfolio_pack,
            summary=summary,
            metadata=result.metadata,
        )
        validate_release_readiness_result(result)
        return result
    except ReleaseReadinessError:
        raise
    except Exception as exc:
        raise ReleaseValidationError(f"release readiness workflow failed: {exc}") from exc


def run_and_persist_release_readiness(
    engine: Engine | None = None,
    release_config: ReleaseReadinessConfig | None = None,
    persistence_config: ReleasePersistenceConfig | None = None,
    write_artefacts: bool = True,
) -> tuple[ReleaseReadinessResult, ReleasePersistenceResult | None]:
    """Run release readiness and optionally write artefacts and database rows."""

    from graph_aml.release.artefacts import generate_release_readiness_artefacts
    from graph_aml.release.persistence import (
        persist_release_readiness_result,
    )
    from graph_aml.release.readiness_inputs import read_release_readiness_inputs

    resolved = release_config or ReleaseReadinessConfig()
    try:
        inputs = read_release_readiness_inputs(engine, resolved)
        result = run_release_readiness_from_inputs(inputs, resolved)
        if write_artefacts and resolved.persistence.write_artefacts:
            generate_release_readiness_artefacts(result, resolved.persistence.artefact_output_dir)
        persisted: ReleasePersistenceResult | None = None
        if engine is not None and resolved.persistence.write_database:
            persisted = persist_release_readiness_result(
                engine,
                result,
                resolved,
                persistence_config,
            )
        return result, persisted
    except ReleaseReadinessError:
        raise
    except Exception as exc:
        raise ReleaseValidationError(f"release readiness run failed: {exc}") from exc
