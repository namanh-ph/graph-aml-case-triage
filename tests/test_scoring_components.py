"""Tests for account risk component scoring."""

import pandas as pd

from graph_aml.scoring import (
    build_account_risk_components,
    clip_score,
    compute_anomaly_risk_component,
    compute_customer_risk_component,
    compute_graph_risk_component,
    compute_jurisdiction_risk_component,
    compute_rule_risk_component,
    map_risk_rating_to_score,
    map_severity_to_score,
    percentile_rank_score,
)


def accounts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1", "A2"],
            "customer_risk_rating": ["high", "low"],
            "high_risk_country_exposure": [1.0, 0.0],
        }
    )


def test_clip_score_bounds_values() -> None:
    assert clip_score(-5) == 0
    assert clip_score(105) == 100


def test_percentile_rank_scores_are_deterministic() -> None:
    values = pd.Series([2, 1, 2])
    assert percentile_rank_score(values).tolist() == percentile_rank_score(values).tolist()


def test_severity_and_customer_mapping() -> None:
    assert map_severity_to_score("High") == 75
    assert map_risk_rating_to_score("HIGH") == 80


def test_rule_component_aggregates_alert_risk() -> None:
    alerts = pd.DataFrame(
        {"account_id": ["A1", "A1"], "severity": ["high", "critical"], "risk_score_rule": [80, 90]}
    )
    result = compute_rule_risk_component(accounts(), alerts)
    assert result.loc[result["account_id"] == "A1", "alert_count"].iloc[0] == 2
    assert result.loc[result["account_id"] == "A2", "rule_risk_score"].iloc[0] == 0


def test_graph_component_uses_percentiles() -> None:
    graph = pd.DataFrame(
        {
            "account_id": ["A1", "A2"],
            "pagerank_score": [0.2, 0.1],
            "degree": [2, 1],
            "shortest_path_to_flagged": [1, None],
        }
    )
    result = compute_graph_risk_component(accounts(), graph)
    assert result["graph_risk_score"].between(0, 100).all()


def test_anomaly_component_uses_scores() -> None:
    result = compute_anomaly_risk_component(
        accounts(), pd.DataFrame({"account_id": ["A1"], "anomaly_score": [91]})
    )
    assert result.loc[result["account_id"] == "A1", "anomaly_risk_score"].iloc[0] == 91


def test_customer_and_jurisdiction_components() -> None:
    assert compute_customer_risk_component(accounts()).loc[0, "customer_risk_score"] == 80
    assert compute_jurisdiction_risk_component(accounts()).loc[0, "jurisdiction_risk_score"] == 100


def test_component_merger_returns_one_row_per_account_and_coverage() -> None:
    result = build_account_risk_components(
        accounts(),
        pd.DataFrame({"account_id": ["A1"], "severity": ["high"], "risk_score_rule": [75]}),
        pd.DataFrame({"account_id": ["A1"], "pagerank_score": [0.2]}),
        pd.DataFrame({"account_id": ["A1"], "anomaly_score": [91]}),
    )
    assert result["account_id"].tolist() == ["A1", "A2"]
    assert "component_coverage" in result
