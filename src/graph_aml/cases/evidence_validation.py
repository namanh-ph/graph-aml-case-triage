"""Validation helpers for case evidence packs."""

from __future__ import annotations

import json
from typing import Any, cast

import pandas as pd

from graph_aml.cases.evidence_builders import (
    CASE_EVIDENCE_PACK_COLUMNS,
    CASE_EXPLANATION_COLUMNS,
    CaseEvidenceBuildResult,
)
from graph_aml.cases.exceptions import CaseEvidenceValidationError

CASE_EVIDENCE_PERSISTENCE_COLUMNS = CASE_EVIDENCE_PACK_COLUMNS + ("updated_at",)
CASE_EXPLANATION_PERSISTENCE_COLUMNS = CASE_EXPLANATION_COLUMNS + ("updated_at",)


def _json_serialisable(value: object) -> bool:
    try:
        json.dumps(value, default=str)
        return True
    except TypeError:
        return False


def _validate_required(frame: pd.DataFrame, columns: tuple[str, ...], label: str) -> None:
    missing = set(columns).difference(frame.columns)
    if missing:
        raise CaseEvidenceValidationError(f"{label} missing columns: {sorted(missing)}")


def validate_case_evidence_build_result(result: CaseEvidenceBuildResult) -> None:
    """Validate built evidence packs and explanations."""

    _validate_required(result.evidence_packs, CASE_EVIDENCE_PACK_COLUMNS, "evidence_packs")
    _validate_required(result.explanations, CASE_EXPLANATION_COLUMNS, "explanations")
    packs = result.evidence_packs
    explanations = result.explanations
    if packs.empty and explanations.empty:
        return
    if packs["case_id"].isna().any() or explanations["case_id"].isna().any():
        raise CaseEvidenceValidationError("case IDs must be non-null")
    if packs.duplicated(["case_id", "evidence_version"]).any():
        raise CaseEvidenceValidationError("duplicate evidence pack keys")
    if explanations.duplicated(["case_id", "explanation_version"]).any():
        raise CaseEvidenceValidationError("duplicate explanation keys")
    if explanations["explanation_text"].astype(str).str.strip().eq("").any():
        raise CaseEvidenceValidationError("explanation_text must be non-empty")
    json_columns = (
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
    for column in json_columns:
        if not packs[column].map(_json_serialisable).all():
            raise CaseEvidenceValidationError(f"{column} must be JSON serialisable")
    if not explanations["explanation_bullets"].map(_json_serialisable).all():
        raise CaseEvidenceValidationError("explanation_bullets must be JSON serialisable")


def validate_prepared_case_evidence_frames(prepared: dict[str, pd.DataFrame]) -> None:
    """Validate prepared persistence frames."""

    if "evidence_packs" not in prepared or "explanations" not in prepared:
        raise CaseEvidenceValidationError(
            "prepared frames must include evidence_packs and explanations"
        )
    _validate_required(
        prepared["evidence_packs"], CASE_EVIDENCE_PERSISTENCE_COLUMNS, "prepared evidence_packs"
    )
    _validate_required(
        prepared["explanations"], CASE_EXPLANATION_PERSISTENCE_COLUMNS, "prepared explanations"
    )
    result = CaseEvidenceBuildResult(
        prepared["evidence_packs"].loc[:, CASE_EVIDENCE_PACK_COLUMNS],
        prepared["explanations"].loc[:, CASE_EXPLANATION_COLUMNS],
    )
    validate_case_evidence_build_result(result)


def build_case_evidence_quality_summary(result: CaseEvidenceBuildResult) -> dict[str, object]:
    """Build JSON-serialisable quality summary."""

    packs = result.evidence_packs
    explanations = result.explanations
    if packs.empty:
        return {
            "evidence_pack_count": 0,
            "explanation_count": int(len(explanations)),
            "unique_case_count": 0,
            "cases_missing_alerts": 0,
            "cases_missing_transactions": 0,
            "cases_missing_risk_scores": 0,
            "average_chronology_event_count": 0.0,
            "average_review_focus_bullet_count": 0.0,
        }
    quality = packs["evidence_quality"]
    chronology = packs["chronology"]
    focus = packs["recommended_review_focus"]
    return {
        "evidence_pack_count": int(len(packs)),
        "explanation_count": int(len(explanations)),
        "unique_case_count": int(packs["case_id"].nunique(dropna=True)),
        "cases_missing_alerts": int(
            quality.apply(lambda item: not item.get("has_alerts", False)).sum()
        ),
        "cases_missing_transactions": int(
            quality.apply(lambda item: not item.get("has_transactions", False)).sum()
        ),
        "cases_missing_risk_scores": int(
            quality.apply(lambda item: not item.get("has_risk_scores", False)).sum()
        ),
        "average_chronology_event_count": float(
            chronology.apply(lambda item: len(cast(Any, item))).mean()
        ),
        "average_review_focus_bullet_count": float(
            focus.apply(lambda item: len(cast(Any, item))).mean()
        ),
    }


def compare_case_evidence_row_counts(
    source_evidence: pd.DataFrame,
    persisted_evidence: pd.DataFrame,
) -> dict[str, object]:
    """Compare source and persisted evidence row counts."""

    source_count = int(len(source_evidence))
    persisted_count = int(len(persisted_evidence))
    warnings: list[str] = []
    if source_count != persisted_count:
        warnings.append("source and persisted row counts differ")
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }
