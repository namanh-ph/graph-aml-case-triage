"""Tests for composite case risk scoring."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CASE_RISK_COMPONENT_COLUMNS,
    CASE_RISK_SCORE_COLUMNS,
    CaseRiskComputationError,
    CaseRiskScoreResult,
    CaseRiskScoringConfig,
    assign_case_risk_band,
    compute_case_risk_scores,
)


def components() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["C1", 90, 80, 70, 60, 50, 40, 90, 80, 80, 70, 70, 60, 60, 50, 2, 2, 1, 2, 150, 1.0],
            ["C2", 20, 30, 10, 40, 25, 10, 20, 20, 30, 30, 10, 10, 40, 40, 1, 1, 1, 1, 20, 1.0],
        ],
        columns=CASE_RISK_COMPONENT_COLUMNS,
    )


def test_risk_band_assignment() -> None:
    assert assign_case_risk_band(91) == "critical"
    assert assign_case_risk_band(80) == "high"
    assert assign_case_risk_band(60) == "medium"
    assert assign_case_risk_band(10) == "low"


def test_case_risk_scoring_returns_result_and_columns() -> None:
    result = compute_case_risk_scores(components())
    assert isinstance(result, CaseRiskScoreResult)
    assert tuple(result.scores.columns) == CASE_RISK_SCORE_COLUMNS
    assert result.scores["case_risk_score"].between(0, 100).all()
    assert result.scores["risk_rank"].tolist() == [1, 2]
    assert "risk_band_counts" in result.summary


def test_case_risk_scoring_uses_configured_weights() -> None:
    config = CaseRiskScoringConfig(
        weights={
            "alert_risk_score": 1.0,
            "account_risk_score": 0.0,
            "graph_risk_score": 0.0,
            "anomaly_risk_score": 0.0,
            "typology_diversity_score": 0.0,
            "evidence_value_score": 0.0,
        }
    )
    result = compute_case_risk_scores(components(), config)
    assert result.scores.loc[result.scores["case_id"] == "C1", "case_risk_score"].iloc[0] == 90


def test_empty_or_malformed_components_raise() -> None:
    with pytest.raises(CaseRiskComputationError):
        compute_case_risk_scores(pd.DataFrame())
    with pytest.raises(CaseRiskComputationError):
        compute_case_risk_scores(pd.DataFrame({"case_id": ["C1"]}))


def test_case_risk_scoring_does_not_mutate_inputs() -> None:
    frame = components()
    original = frame.copy(deep=True)
    compute_case_risk_scores(frame)
    pd.testing.assert_frame_equal(frame, original)
