"""Summary helpers for release readiness outputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from graph_aml.release.portfolio_pack import ReleasePortfolioPack

if TYPE_CHECKING:
    from graph_aml.release.validation import ReleaseReadinessResult


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    values = frame[column].fillna("").astype(str).value_counts().sort_index().to_dict()
    return {str(key): int(value) for key, value in values.items()}


def _status_summary(frame: pd.DataFrame) -> dict[str, object]:
    counts = _value_counts(frame, "status")
    return {
        "row_count": int(len(frame)),
        "pass_count": counts.get("pass", 0),
        "warning_count": counts.get("warning", 0),
        "failure_count": counts.get("fail", 0),
        "status_counts": counts,
    }


def summarise_repository_checks(checks: pd.DataFrame) -> dict[str, object]:
    return {**_status_summary(checks), "item_type_counts": _value_counts(checks, "item_type")}


def summarise_documentation_checks(checks: pd.DataFrame) -> dict[str, object]:
    return {
        **_status_summary(checks),
        "document_count": int(checks["document_path"].nunique())
        if "document_path" in checks.columns
        else 0,
    }


def summarise_artefact_checks(checks: pd.DataFrame) -> dict[str, object]:
    required_count = (
        int(checks["required"].map(bool).sum())
        if not checks.empty and "required" in checks.columns
        else 0
    )
    return {
        **_status_summary(checks),
        "required_count": required_count,
        "artefact_type_counts": _value_counts(checks, "artefact_type"),
    }


def summarise_evidence_index(evidence: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(evidence)),
        "evidence_type_counts": _value_counts(evidence, "evidence_type"),
    }


def summarise_portfolio_pack(pack: ReleasePortfolioPack) -> dict[str, object]:
    return {
        "release_run_id": pack.release_run_id,
        "section_count": 5,
        "validation_index_count": int(len(pack.validation_index)),
        "evidence_item_count": int(len(pack.evidence_index)),
    }


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        return int(value)
    return 0


def release_readiness_result_to_dict(result: ReleaseReadinessResult) -> dict[str, object]:
    """Convert a ReleaseReadinessResult-like object to JSON-serialisable dict."""

    repository = summarise_repository_checks(result.repository_checks)
    docs = summarise_documentation_checks(result.documentation_checks)
    artefacts = summarise_artefact_checks(result.artefact_checks)
    evidence = summarise_evidence_index(result.evidence_index)
    failed = (
        _as_int(repository["failure_count"])
        + _as_int(docs["failure_count"])
        + _as_int(artefacts["failure_count"])
    )
    warnings = (
        _as_int(repository["warning_count"])
        + _as_int(docs["warning_count"])
        + _as_int(artefacts["warning_count"])
    )
    return {
        "release_run_id": result.release_run_id,
        "summary": result.summary,
        "metadata": result.metadata,
        "repository": repository,
        "documentation": docs,
        "artefacts": artefacts,
        "evidence": evidence,
        "portfolio_pack": summarise_portfolio_pack(result.portfolio_pack),
        "release_status": "not_ready" if failed else "ready_with_warnings" if warnings else "ready",
    }
