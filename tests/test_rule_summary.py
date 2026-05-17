"""Tests for AML rule alert summaries."""

import json

from graph_aml.alerts import create_alert_record
from graph_aml.rules import summarise_rule_alerts


def _alerts():
    return (
        create_alert_record(
            "AL_001",
            "ACC_1",
            "CUST_1",
            "Structuring",
            "structuring",
            "high",
            80,
            "3 transfers below threshold within 24 hours",
            ["TXN_1", "TXN_2"],
            "2025-01-01T00:00:00Z",
            "2025-01-01T02:00:00Z",
        ),
        create_alert_record(
            "AL_002",
            "ACC_2",
            "CUST_2",
            "Structuring",
            "structuring",
            "critical",
            90,
            "4 transfers below threshold within 24 hours",
            ["TXN_3"],
            "2025-01-02T00:00:00Z",
            "2025-01-02T02:00:00Z",
        ),
    )


def test_summarise_rule_alerts_handles_empty_alerts() -> None:
    assert summarise_rule_alerts(())["alert_count"] == 0


def test_rule_summary_includes_all_expected_keys() -> None:
    summary = summarise_rule_alerts(_alerts())

    assert {
        "alert_count",
        "unique_account_count",
        "unique_customer_count",
        "severity_counts",
        "typology_counts",
        "rule_name_counts",
        "evidence_transaction_count",
        "min_detection_window_start",
        "max_detection_window_end",
        "mean_rule_score",
        "max_rule_score",
    }.issubset(summary)


def test_rule_summary_alert_count_is_correct() -> None:
    assert summarise_rule_alerts(_alerts())["alert_count"] == 2


def test_rule_summary_unique_account_count_is_correct() -> None:
    assert summarise_rule_alerts(_alerts())["unique_account_count"] == 2


def test_rule_summary_severity_counts_are_correct() -> None:
    assert summarise_rule_alerts(_alerts())["severity_counts"] == {"critical": 1, "high": 1}


def test_rule_summary_typology_counts_are_correct() -> None:
    assert summarise_rule_alerts(_alerts())["typology_counts"] == {"structuring": 2}


def test_rule_summary_evidence_transaction_count_is_correct() -> None:
    assert summarise_rule_alerts(_alerts())["evidence_transaction_count"] == 3


def test_rule_summary_mean_and_max_rule_scores_are_correct() -> None:
    summary = summarise_rule_alerts(_alerts())

    assert summary["mean_rule_score"] == 85.0
    assert summary["max_rule_score"] == 90.0


def test_rule_summary_is_json_serialisable() -> None:
    json.dumps(summarise_rule_alerts(_alerts()))


def test_rule_summary_handles_fan_in_alert_counts() -> None:
    alerts = (
        create_alert_record(
            "AL_FAN_IN_001",
            "ACC_COLLECT_001",
            "CUST_COLLECT_001",
            "Fan-in",
            "fan_in",
            "high",
            80,
            "15 unique senders within 7 days",
            ["TXN_FAN_001", "TXN_FAN_002"],
            "2025-01-01T00:00:00Z",
            "2025-01-02T00:00:00Z",
        ),
    )

    summary = summarise_rule_alerts(alerts)

    assert summary["typology_counts"] == {"fan_in": 1}
    assert summary["rule_name_counts"] == {"Fan-in": 1}
    assert summary["evidence_transaction_count"] == 2


def test_rule_summary_handles_fan_out_alert_counts() -> None:
    alerts = (
        create_alert_record(
            "AL_FAN_OUT_001",
            "ACC_DISPERSE_001",
            "CUST_DISPERSE_001",
            "Fan-out",
            "fan_out",
            "high",
            80,
            "20 unique recipients within 7 days",
            ["TXN_FAN_OUT_001", "TXN_FAN_OUT_002", "TXN_FAN_OUT_003"],
            "2025-01-01T00:00:00Z",
            "2025-01-02T00:00:00Z",
        ),
    )

    summary = summarise_rule_alerts(alerts)

    assert summary["typology_counts"] == {"fan_out": 1}
    assert summary["rule_name_counts"] == {"Fan-out": 1}
    assert summary["evidence_transaction_count"] == 3


def test_rule_summary_handles_rapid_movement_alert_counts() -> None:
    alerts = (
        create_alert_record(
            "AL_RAPID_MOVEMENT_001",
            "ACC_PASS_001",
            "CUST_PASS_001",
            "Rapid movement",
            "rapid_movement",
            "high",
            80,
            "90 percent of received value sent out within 48 hours",
            ["TXN_RM_IN_001", "TXN_RM_OUT_001"],
            "2025-01-01T00:00:00Z",
            "2025-01-03T00:00:00Z",
        ),
    )

    summary = summarise_rule_alerts(alerts)

    assert summary["typology_counts"] == {"rapid_movement": 1}
    assert summary["rule_name_counts"] == {"Rapid movement": 1}
    assert summary["evidence_transaction_count"] == 2


def test_rule_summary_handles_dormant_reactivation_alert_counts() -> None:
    alerts = (
        create_alert_record(
            "AL_DORMANT_REACTIVATION_001",
            "ACC_DORMANT_001",
            "CUST_DORMANT_001",
            "Dormant reactivation",
            "dormant_reactivation",
            "high",
            80,
            "120 inactive days followed by 10000.00 outbound value within 7 days",
            ["TXN_DR_PRIOR_001", "TXN_DR_REACT_001"],
            "2025-01-10T00:00:00Z",
            "2025-01-17T00:00:00Z",
        ),
    )

    summary = summarise_rule_alerts(alerts)

    assert summary["typology_counts"] == {"dormant_reactivation": 1}
    assert summary["rule_name_counts"] == {"Dormant reactivation": 1}
    assert summary["evidence_transaction_count"] == 2


def test_rule_summary_handles_circular_flow_alert_counts() -> None:
    alerts = (
        create_alert_record(
            "AL_CIRCULAR_FLOW_001",
            "ACC_CF_A",
            "CUST_CF_A",
            "Circular flow",
            "circular_flow",
            "high",
            85,
            "3-account circular flow with 12000.00 total value over 6.0 hours",
            ["TXN_CF_001", "TXN_CF_002", "TXN_CF_003"],
            "2025-01-01T00:00:00Z",
            "2025-01-01T06:00:00Z",
        ),
    )

    summary = summarise_rule_alerts(alerts)

    assert summary["typology_counts"] == {"circular_flow": 1}
    assert summary["rule_name_counts"] == {"Circular flow": 1}
    assert summary["evidence_transaction_count"] == 3
