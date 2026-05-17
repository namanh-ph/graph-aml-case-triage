"""Tests for case risk component scoring."""

import pandas as pd

from graph_aml.cases import (
    CASE_RISK_COMPONENT_COLUMNS,
    build_case_risk_components,
    clip_case_score,
    compute_case_account_risk_component,
    compute_case_alert_risk_component,
    compute_case_anomaly_risk_component,
    compute_case_evidence_value_component,
    compute_case_graph_risk_component,
    compute_case_typology_diversity_component,
    map_case_alert_severity_to_score,
    percentile_rank_score,
)


def cases() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": ["C1", "C2"],
            "primary_account_id": ["A1", "A2"],
            "related_accounts": [["A1"], ["A2"]],
            "alert_ids": [["AL1", "AL2"], ["AL3"]],
            "typologies": [["structuring", "fan_out"], ["fan_in"]],
            "evidence_transaction_count": [2, 1],
            "total_transaction_value": [150.0, 20.0],
        }
    )


def test_score_helpers() -> None:
    assert clip_case_score(-1) == 0
    assert clip_case_score(101) == 100
    assert (
        percentile_rank_score(pd.Series([2, 1, 2])).tolist()
        == percentile_rank_score(pd.Series([2, 1, 2])).tolist()
    )
    assert map_case_alert_severity_to_score("High") == 75


def test_component_builders_and_merger_do_not_mutate_inputs() -> None:
    source_cases = cases()
    original = source_cases.copy(deep=True)
    case_alerts = pd.DataFrame({"case_id": ["C1", "C1", "C2"], "alert_id": ["AL1", "AL2", "AL3"]})
    alerts = pd.DataFrame(
        {
            "alert_id": ["AL1", "AL2", "AL3"],
            "severity": ["high", "critical", "medium"],
            "risk_score_rule": [80, 90, 50],
            "typology": ["structuring", "fan_out", "fan_in"],
        }
    )
    account = pd.DataFrame({"account_id": ["A1", "A2"], "account_risk_score": [88, 40]})
    graph = pd.DataFrame(
        {
            "account_id": ["A1", "A2"],
            "pagerank_score": [0.2, 0.1],
            "degree_centrality": [0.5, 0.1],
            "cycle_count": [2, 0],
            "community_size": [5, 1],
            "high_risk_alert_count": [1, 0],
            "shortest_path_to_flagged": [1, None],
        }
    )
    anomaly = pd.DataFrame({"account_id": ["A1", "A2"], "anomaly_score": [91, 20]})
    transactions = pd.DataFrame()
    assert (
        compute_case_alert_risk_component(source_cases, case_alerts, alerts).loc[0, "alert_count"]
        == 2
    )
    assert (
        compute_case_account_risk_component(source_cases, account).loc[0, "account_risk_score"]
        == 88
    )
    assert (
        compute_case_graph_risk_component(source_cases, graph)["graph_risk_score"]
        .between(0, 100)
        .all()
    )
    assert (
        compute_case_anomaly_risk_component(source_cases, anomaly).loc[0, "max_anomaly_score"] == 91
    )
    assert (
        compute_case_typology_diversity_component(source_cases, alerts).loc[0, "typology_count"]
        == 2
    )
    assert (
        compute_case_evidence_value_component(source_cases, transactions).loc[
            0, "total_transaction_value"
        ]
        == 150
    )
    merged = build_case_risk_components(
        source_cases,
        case_alerts,
        alerts,
        account,
        graph,
        anomaly,
        transactions,
    )
    assert tuple(merged.columns) == CASE_RISK_COMPONENT_COLUMNS
    assert merged["component_coverage"].between(0, 1).all()
    pd.testing.assert_frame_equal(source_cases, original)
