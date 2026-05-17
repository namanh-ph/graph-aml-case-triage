"""Tests for case risk validation and summaries."""

import json

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseRiskValidationError,
    build_case_risk_score_quality_summary,
    case_risk_score_result_to_dict,
    compare_case_risk_score_row_counts,
    summarise_case_risk_components,
    summarise_case_risk_scores,
    validate_case_risk_component_frame,
    validate_case_risk_score_frame,
    validate_prepared_case_risk_score_frame,
)
from graph_aml.cases.risk_validation import CASE_RISK_PERSISTENCE_COLUMNS
from tests.fixtures.case_risk import case_risk_components, case_risk_score_result


def test_valid_component_and_score_frames_pass_validation() -> None:
    validate_case_risk_component_frame(case_risk_components())
    validate_case_risk_score_frame(case_risk_score_result().scores)


def test_invalid_score_frames_fail_validation() -> None:
    scores = case_risk_score_result().scores.copy()
    scores.loc[0, "case_id"] = None
    with pytest.raises(CaseRiskValidationError):
        validate_case_risk_score_frame(scores)
    scores = pd.concat([case_risk_score_result().scores, case_risk_score_result().scores])
    with pytest.raises(CaseRiskValidationError):
        validate_case_risk_score_frame(scores)
    scores = case_risk_score_result().scores.copy()
    scores.loc[0, "case_risk_score"] = 101
    with pytest.raises(CaseRiskValidationError):
        validate_case_risk_score_frame(scores)
    scores = case_risk_score_result().scores.copy()
    scores.loc[0, "risk_band"] = "bad"
    with pytest.raises(CaseRiskValidationError):
        validate_case_risk_score_frame(scores)


def test_prepared_score_frame_validation() -> None:
    prepared = case_risk_score_result().scores.assign(
        weights=[{}], metadata=[{}], scored_at=["now"]
    )
    validate_prepared_case_risk_score_frame(prepared.loc[:, CASE_RISK_PERSISTENCE_COLUMNS])
    with pytest.raises(CaseRiskValidationError):
        validate_prepared_case_risk_score_frame(case_risk_score_result().scores)


def test_quality_comparison_and_summaries_are_serialisable() -> None:
    result = case_risk_score_result()
    quality = build_case_risk_score_quality_summary(result.scores)
    assert quality["risk_band_counts"]["high"] == 1
    assert compare_case_risk_score_row_counts(result.scores, result.scores)["status"] == "ok"
    warning = compare_case_risk_score_row_counts(result.scores, pd.DataFrame())
    assert warning["status"] == "warning"
    json.dumps(summarise_case_risk_components(case_risk_components()), default=str)
    json.dumps(summarise_case_risk_scores(result.scores), default=str)
    json.dumps(case_risk_score_result_to_dict(result), default=str)
