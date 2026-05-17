"""Tests for alert summary utilities."""

from __future__ import annotations

import json

from graph_aml.alerts import create_alert_record, summarise_alerts


def _alerts():
    return [
        create_alert_record(
            "AL_001",
            "ACC_001",
            "CUST_001",
            "Structuring",
            "structuring",
            "high",
            80,
            "STRUCTURING",
            ["TXN_001", "TXN_002"],
            "2025-01-01T00:00:00Z",
            "2025-01-02T00:00:00Z",
        ),
        create_alert_record(
            "AL_002",
            "ACC_002",
            "CUST_001",
            "Fan In",
            "fan_in",
            "medium",
            60,
            "FAN_IN",
            ["TXN_003"],
            "2025-01-03T00:00:00Z",
            "2025-01-04T00:00:00Z",
        ),
    ]


def test_summarise_alerts_handles_empty_inputs() -> None:
    assert summarise_alerts([])["alert_count"] == 0


def test_summary_includes_all_expected_keys() -> None:
    summary = summarise_alerts(_alerts())

    assert set(summary) == {
        "alert_count",
        "unique_account_count",
        "unique_customer_count",
        "severity_counts",
        "status_counts",
        "rule_name_counts",
        "typology_counts",
        "min_detection_window_start",
        "max_detection_window_end",
        "mean_rule_score",
        "max_rule_score",
        "evidence_id_count",
    }


def test_alert_count_is_correct() -> None:
    assert summarise_alerts(_alerts())["alert_count"] == 2


def test_unique_account_count_is_correct() -> None:
    assert summarise_alerts(_alerts())["unique_account_count"] == 2


def test_unique_customer_count_is_correct() -> None:
    assert summarise_alerts(_alerts())["unique_customer_count"] == 1


def test_severity_counts_are_correct() -> None:
    assert summarise_alerts(_alerts())["severity_counts"] == {"high": 1, "medium": 1}


def test_status_counts_are_correct() -> None:
    assert summarise_alerts(_alerts())["status_counts"] == {"New": 2}


def test_rule_name_counts_are_correct() -> None:
    assert summarise_alerts(_alerts())["rule_name_counts"] == {"Fan In": 1, "Structuring": 1}


def test_typology_counts_are_correct() -> None:
    assert summarise_alerts(_alerts())["typology_counts"] == {"fan_in": 1, "structuring": 1}


def test_mean_and_max_rule_scores_are_correct() -> None:
    summary = summarise_alerts(_alerts())

    assert summary["mean_rule_score"] == 70.0
    assert summary["max_rule_score"] == 80.0


def test_evidence_id_count_is_correct() -> None:
    assert summarise_alerts(_alerts())["evidence_id_count"] == 3


def test_summary_is_json_serialisable() -> None:
    json.dumps(summarise_alerts(_alerts()), sort_keys=True)
