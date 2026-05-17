"""Tests for generated AML case records."""

import pandas as pd

from graph_aml.cases import (
    build_case_groups,
    build_case_summary_text,
    generate_cases_from_groups,
)


def inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    alerts = pd.DataFrame(
        {
            "alert_id": ["AL1", "AL2"],
            "account_id": ["A1", "A1"],
            "customer_id": ["C1", "C1"],
            "typology": ["structuring", "fan_out"],
            "rule_name": ["Structuring", "Fan-out"],
            "severity": ["high", "critical"],
            "risk_score_rule": [80, 90],
            "evidence_ids": [["T1"], ["T2"]],
        }
    )
    accounts = pd.DataFrame({"account_id": ["A1"], "customer_id": ["C1"]})
    risk = pd.DataFrame({"account_id": ["A1"], "account_risk_score": [88]})
    transactions = pd.DataFrame(
        {"transaction_id": ["T1", "T2"], "amount": [100.0, 50.0], "counterparty_id": ["CP1", "CP2"]}
    )
    return alerts, accounts, risk, transactions


def test_cases_links_and_fields_are_generated() -> None:
    alerts, accounts, risk, transactions = inputs()
    groups = build_case_groups(alerts, accounts, pd.DataFrame(), transactions)
    result = generate_cases_from_groups(groups, alerts, risk, transactions)
    assert not result.cases.empty
    assert not result.case_alerts.empty
    assert not result.case_entities.empty
    row = result.cases.iloc[0]
    assert row["case_id"] == result.cases.iloc[0]["case_id"]
    assert row["primary_account_id"] == "A1"
    assert row["primary_customer_id"] == "C1"
    assert set(row["typologies"]) == {"structuring", "fan_out"}
    assert row["total_transaction_value"] == 150.0
    assert row["priority_score"] >= 90
    assert row["severity"] == "critical"
    assert row["status"] == "New"


def test_summary_text_is_deterministic() -> None:
    row = {
        "alert_count": 2,
        "unique_typology_count": 1,
        "primary_account_id": "A1",
        "severity": "high",
        "priority_score": 80,
        "grouping_strategy": "account",
    }
    assert build_case_summary_text(row) == build_case_summary_text(row)


def test_generation_does_not_mutate_inputs() -> None:
    alerts, accounts, risk, transactions = inputs()
    original = alerts.copy(deep=True)
    groups = build_case_groups(alerts, accounts, pd.DataFrame(), transactions)
    generate_cases_from_groups(groups, alerts, risk, transactions)
    pd.testing.assert_frame_equal(alerts, original)
