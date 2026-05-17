"""Tests for scoring validation and summaries."""

import json

import pandas as pd
import pytest

from graph_aml.scoring import (
    ScoringValidationError,
    build_account_risk_score_quality_summary,
    compare_account_risk_score_row_counts,
    compute_account_risk_scores,
    summarise_account_risk_scores,
    summarise_risk_components,
    validate_account_risk_score_frame,
    validate_prepared_account_risk_score_frame,
    validate_risk_component_frame,
)
from graph_aml.scoring.persistence import prepare_account_risk_scores_for_persistence
from tests.test_scoring_composite import components


def test_valid_frames_pass_validation() -> None:
    component_frame = components()
    validate_risk_component_frame(component_frame)
    result = compute_account_risk_scores(component_frame)
    validate_account_risk_score_frame(result.scores)
    validate_prepared_account_risk_score_frame(prepare_account_risk_scores_for_persistence(result))


def test_invalid_scores_fail_validation() -> None:
    result = compute_account_risk_scores(components())
    bad = result.scores.copy()
    bad.loc[0, "account_risk_score"] = 101
    with pytest.raises(ScoringValidationError):
        validate_account_risk_score_frame(bad)


def test_duplicate_accounts_fail_validation() -> None:
    duplicate = pd.concat([components(), components().iloc[[0]]], ignore_index=True)
    with pytest.raises(ScoringValidationError):
        validate_risk_component_frame(duplicate)


def test_quality_and_summary_payloads_are_json_serialisable() -> None:
    result = compute_account_risk_scores(components())
    payloads = [
        build_account_risk_score_quality_summary(result.scores),
        compare_account_risk_score_row_counts(result.scores, result.scores),
        summarise_account_risk_scores(result.scores),
        summarise_risk_components(result.components),
    ]
    for payload in payloads:
        json.dumps(payload, default=str)
