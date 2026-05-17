"""Tests for account profile metrics and components."""

import pandas as pd

from graph_aml.dashboard.account_components import (
    render_account_alerts,
    render_account_cases,
    render_account_counterparties,
    render_account_features,
    render_account_header,
    render_account_metric_cards,
    render_account_transactions,
)
from graph_aml.dashboard.account_metrics import (
    build_account_alert_summary,
    build_account_case_summary,
    build_account_profile_metrics,
    build_account_transaction_summary,
)


def test_account_profile_metrics_include_expected_values() -> None:
    transactions = pd.DataFrame(
        {
            "sender_account_id": ["A1", "A2"],
            "receiver_account_id": ["A2", "A1"],
            "counterparty_id": [None, None],
            "amount": [100.0, 40.0],
        }
    )
    alerts = pd.DataFrame({"severity": ["high"]})
    cases = pd.DataFrame({"case_risk_score": [95.0]})
    profile = {
        "transactions": transactions,
        "alerts": alerts,
        "cases": cases,
        "account_risk_scores": pd.DataFrame({"account_risk_score": [91.0]}),
        "anomaly_scores": pd.DataFrame({"anomaly_score": [88.0]}),
        "graph_features": pd.DataFrame({"community_id": [7]}),
    }

    metrics = build_account_profile_metrics(profile)

    assert metrics["transaction_count"] == 2
    assert metrics["total_sent"] == 100.0
    assert metrics["total_received"] == 40.0
    assert metrics["net_flow"] == -60.0
    assert metrics["alert_count"] == 1
    assert metrics["linked_case_count"] == 1
    assert metrics["latest_account_risk_score"] == 91.0
    assert metrics["latest_anomaly_score"] == 88.0


def test_account_summaries_handle_empty_inputs() -> None:
    assert build_account_transaction_summary(pd.DataFrame())["transaction_count"] == 0
    assert build_account_alert_summary(pd.DataFrame())["alert_count"] == 0
    assert build_account_case_summary(pd.DataFrame())["linked_case_count"] == 0


def test_account_components_are_callable_with_empty_frames() -> None:
    render_account_header(pd.DataFrame())
    render_account_metric_cards({"transaction_count": 0})
    render_account_transactions(pd.DataFrame())
    render_account_alerts(pd.DataFrame())
    render_account_cases(pd.DataFrame())
    render_account_features({"graph_features": pd.DataFrame()})
    render_account_counterparties(pd.DataFrame())


def test_metric_helpers_do_not_mutate_inputs() -> None:
    transactions = pd.DataFrame({"sender_account_id": ["A1"], "amount": [1.0]})
    original = transactions.copy(deep=True)

    build_account_transaction_summary(transactions)

    pd.testing.assert_frame_equal(transactions, original)
