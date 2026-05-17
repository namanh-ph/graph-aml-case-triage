"""Tests for case grouping orchestration."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseGenerationConfig,
    CaseGroupingConfig,
    CaseGroupingError,
    build_case_groups,
)


def alerts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "alert_id": ["AL1", "AL2"],
            "account_id": ["A1", "A1"],
            "customer_id": ["C1", "C1"],
            "typology": ["structuring", "fan_out"],
            "rule_name": ["Structuring", "Fan-out"],
            "severity": ["high", "medium"],
            "risk_score_rule": [80, 60],
            "evidence_ids": [["T1"], ["T2"]],
        }
    )


def test_enabled_grouping_strategies_are_executed() -> None:
    result = build_case_groups(
        alerts(),
        pd.DataFrame({"account_id": ["A1"], "customer_id": ["C1"]}),
        pd.DataFrame({"account_id": ["A1"], "community_id": [1]}),
        pd.DataFrame({"transaction_id": ["T1"], "counterparty_id": ["CP1"]}),
    )
    assert {"account", "customer", "graph_community"}.issubset(set(result["grouping_strategy"]))


def test_disabled_grouping_strategies_are_skipped() -> None:
    config = CaseGenerationConfig(
        grouping=CaseGroupingConfig(
            group_by_account=True,
            group_by_customer=False,
            group_by_graph_community=False,
            group_by_circular_flow=False,
            group_by_common_counterparty=False,
        )
    )
    result = build_case_groups(alerts(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), config)
    assert result["grouping_strategy"].tolist() == ["account"]


def test_empty_alerts_produce_empty_group_frame() -> None:
    result = build_case_groups(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert result.empty


def test_groups_are_deduplicated_and_sorted_deterministically() -> None:
    config = CaseGenerationConfig(
        grouping=CaseGroupingConfig(
            group_by_account=True,
            group_by_customer=False,
            group_by_graph_community=False,
            group_by_circular_flow=False,
            group_by_common_counterparty=False,
        )
    )
    result = build_case_groups(
        alerts(),
        pd.DataFrame({"account_id": ["A1"], "customer_id": ["C1"]}),
        pd.DataFrame(),
        pd.DataFrame(),
        config,
    )
    assert result["case_group_id"].is_unique
    assert result["primary_account_id"].tolist() == sorted(result["primary_account_id"].tolist())


def test_max_cases_limits_are_enforced() -> None:
    config = CaseGenerationConfig(
        grouping=CaseGroupingConfig(
            group_by_account=True,
            group_by_customer=False,
            group_by_graph_community=False,
            group_by_circular_flow=False,
            group_by_common_counterparty=False,
        )
    )
    result = build_case_groups(alerts(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), config)
    assert len(result) <= config.thresholds.max_cases_total


def test_failures_raise_case_grouping_error() -> None:
    with pytest.raises(CaseGroupingError):
        build_case_groups(
            pd.DataFrame({"alert_id": ["AL1"]}), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )
