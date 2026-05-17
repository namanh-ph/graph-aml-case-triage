"""Tests for individual case grouping strategies."""

import pandas as pd

from graph_aml.cases import (
    CASE_GROUP_COLUMNS,
    CaseGenerationConfig,
    CaseGenerationThresholdConfig,
    group_alerts_by_account,
    group_alerts_by_circular_flow,
    group_alerts_by_common_counterparty,
    group_alerts_by_customer,
    group_alerts_by_graph_community,
)


def alerts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "alert_id": ["AL1", "AL2", "AL3"],
            "account_id": ["A1", "A1", "A2"],
            "customer_id": [None, None, "C2"],
            "typology": ["structuring", "circular_flow", "fan_in"],
            "rule_name": ["Structuring", "Circular flow", "Fan-in"],
            "severity": ["high", "critical", "medium"],
            "risk_score_rule": [80, 95, 55],
            "evidence_ids": [["T1"], ["T2", "T3"], ["T3"]],
        }
    )


def accounts() -> pd.DataFrame:
    return pd.DataFrame({"account_id": ["A1", "A2"], "customer_id": ["C1", "C2"]})


def graph_features() -> pd.DataFrame:
    return pd.DataFrame({"account_id": ["A1", "A2"], "community_id": [7, 7]})


def transactions() -> pd.DataFrame:
    return pd.DataFrame(
        {"transaction_id": ["T1", "T2", "T3"], "counterparty_id": ["CP1", "CP2", "CP2"]}
    )


def test_account_grouping_produces_one_group_per_alerted_account() -> None:
    result = group_alerts_by_account(alerts(), accounts())
    assert set(result["primary_account_id"]) == {"A1", "A2"}


def test_customer_grouping_joins_accounts_to_customers() -> None:
    result = group_alerts_by_customer(alerts(), accounts())
    assert set(result["primary_customer_id"]) == {"C1", "C2"}


def test_graph_community_grouping_groups_same_community() -> None:
    result = group_alerts_by_graph_community(alerts(), graph_features())
    assert len(result) == 1
    assert set(result.iloc[0]["account_ids"]) == {"A1", "A2"}


def test_circular_flow_grouping_groups_circular_alerts() -> None:
    result = group_alerts_by_circular_flow(alerts())
    assert len(result) == 1
    assert result.iloc[0]["grouping_strategy"] == "circular_flow"


def test_common_counterparty_grouping_joins_evidence_transactions() -> None:
    result = group_alerts_by_common_counterparty(alerts(), transactions())
    assert "common_counterparty" in result["grouping_strategy"].tolist()


def test_groups_respect_min_and_max_alert_thresholds() -> None:
    config = CaseGenerationConfig(
        thresholds=CaseGenerationThresholdConfig(min_alerts_per_case=2, max_alerts_per_case=2)
    )
    result = group_alerts_by_account(alerts(), accounts(), config)
    assert result["primary_account_id"].tolist() == ["A1"]


def test_groups_respect_max_alerts_per_case() -> None:
    config = CaseGenerationConfig(thresholds=CaseGenerationThresholdConfig(max_alerts_per_case=1))
    result = group_alerts_by_account(alerts(), accounts(), config)
    assert max(len(ids) for ids in result["alert_ids"]) == 1


def test_grouping_output_columns_and_mutation_safety() -> None:
    source = alerts()
    original = source.copy(deep=True)
    result = group_alerts_by_account(source, accounts())
    assert tuple(result.columns) == CASE_GROUP_COLUMNS
    pd.testing.assert_frame_equal(source, original)
