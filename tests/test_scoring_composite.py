"""Tests for composite account risk scoring."""

from datetime import date

import pandas as pd
import pytest

from graph_aml.scoring import (
    ACCOUNT_RISK_SCORE_COLUMNS,
    AccountRiskScoreResult,
    AccountRiskScoringConfig,
    ScoringComputationError,
    assign_account_risk_band,
    compute_account_risk_scores,
)


def components() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1", "A2"],
            "rule_risk_score": [100, 0],
            "graph_risk_score": [100, 0],
            "anomaly_risk_score": [100, 0],
            "customer_risk_score": [100, 20],
            "jurisdiction_risk_score": [100, 30],
            "alert_count": [2, 0],
            "high_severity_alert_count": [1, 0],
            "critical_severity_alert_count": [1, 0],
            "max_rule_alert_score": [100, 0],
            "mean_rule_alert_score": [90, 0],
            "max_anomaly_score": [100, 0],
            "graph_percentile_score": [100, 0],
            "component_coverage": [1.0, 0.4],
        }
    )


def test_risk_band_assignment_respects_thresholds() -> None:
    assert assign_account_risk_band(91) == "critical"
    assert assign_account_risk_band(80) == "high"
    assert assign_account_risk_band(60) == "medium"
    assert assign_account_risk_band(10) == "low"


def test_composite_scores_use_weights_and_rank_deterministically() -> None:
    result = compute_account_risk_scores(components(), score_date=date(2026, 5, 7))
    assert isinstance(result, AccountRiskScoreResult)
    assert tuple(result.scores.columns) == ACCOUNT_RISK_SCORE_COLUMNS
    assert result.scores["account_risk_score"].between(0, 100).all()
    assert result.scores["account_id"].tolist() == ["A1", "A2"]
    assert result.summary["risk_band_counts"]


def test_configured_weights_affect_score() -> None:
    config = AccountRiskScoringConfig(
        weights={
            "rule_risk_score": 1,
            "graph_risk_score": 0,
            "anomaly_risk_score": 0,
            "customer_risk_score": 0,
            "jurisdiction_risk_score": 0,
        }
    )
    result = compute_account_risk_scores(components(), config=config)
    assert (
        result.scores.loc[result.scores["account_id"] == "A1", "account_risk_score"].iloc[0] == 100
    )


def test_empty_or_malformed_components_raise() -> None:
    with pytest.raises(ScoringComputationError):
        compute_account_risk_scores(pd.DataFrame())
