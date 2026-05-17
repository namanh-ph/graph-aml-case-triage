"""Tests for case evidence validation and summaries."""

import json

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseEvidenceValidationError,
    build_case_evidence_quality_summary,
    case_evidence_build_result_to_dict,
    compare_case_evidence_row_counts,
    summarise_case_evidence_packs,
    summarise_case_explanations,
    validate_case_evidence_build_result,
    validate_prepared_case_evidence_frames,
)
from graph_aml.cases.evidence_persistence import prepare_case_evidence_for_persistence
from tests.fixtures.case_evidence import evidence_result


def test_valid_evidence_result_and_prepared_frames_pass_validation() -> None:
    result = evidence_result()
    validate_case_evidence_build_result(result)
    validate_prepared_case_evidence_frames(prepare_case_evidence_for_persistence(result))


def test_invalid_evidence_result_fails_validation() -> None:
    result = evidence_result()
    bad = result.evidence_packs.copy()
    bad.loc[0, "case_id"] = None
    with pytest.raises(CaseEvidenceValidationError):
        validate_case_evidence_build_result(type(result)(bad, result.explanations))
    bad = pd.concat([result.evidence_packs, result.evidence_packs])
    with pytest.raises(CaseEvidenceValidationError):
        validate_case_evidence_build_result(type(result)(bad, result.explanations))
    explanations = result.explanations.copy()
    explanations.loc[0, "explanation_text"] = ""
    with pytest.raises(CaseEvidenceValidationError):
        validate_case_evidence_build_result(type(result)(result.evidence_packs, explanations))


def test_quality_comparison_and_summaries_are_serialisable() -> None:
    result = evidence_result()
    quality = build_case_evidence_quality_summary(result)
    assert quality["evidence_pack_count"] == 1
    assert (
        compare_case_evidence_row_counts(result.evidence_packs, result.evidence_packs)["status"]
        == "ok"
    )
    assert (
        compare_case_evidence_row_counts(result.evidence_packs, pd.DataFrame())["status"]
        == "warning"
    )
    json.dumps(summarise_case_evidence_packs(result.evidence_packs), default=str)
    json.dumps(summarise_case_explanations(result.explanations), default=str)
    json.dumps(case_evidence_build_result_to_dict(result), default=str)
