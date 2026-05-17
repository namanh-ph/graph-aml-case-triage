"""Tests for common alert schema records."""

from __future__ import annotations

import json

import pytest

from graph_aml.alerts import (
    ALERT_COLUMNS,
    ALERT_SEVERITIES,
    ALERT_STATUSES,
    AlertRecord,
    AlertValidationError,
    alert_record_from_dict,
    alert_record_to_dict,
    create_alert_record,
)


def _alert() -> AlertRecord:
    return create_alert_record(
        alert_id="AL_STRUCTURING_001",
        account_id="ACC_001",
        customer_id="CUST_001",
        rule_name="Structuring",
        typology="structuring",
        severity="HIGH",
        risk_score_rule=87.5,
        reason_code="STRUCTURING_THRESHOLD",
        evidence_ids=["TXN_001", "TXN_002"],
        detection_window_start="2025-01-01T00:00:00Z",
        detection_window_end="2025-01-02T00:00:00Z",
    )


def test_alert_columns_align_with_aml_alerts_table_columns() -> None:
    assert ALERT_COLUMNS == (
        "alert_id",
        "account_id",
        "customer_id",
        "rule_name",
        "typology",
        "severity",
        "risk_score_rule",
        "reason_code",
        "evidence_ids",
        "detection_window_start",
        "detection_window_end",
        "model_run_id",
        "alert_status",
        "created_at",
        "updated_at",
    )


def test_alert_severities_include_required_values() -> None:
    assert set(ALERT_SEVERITIES) == {"low", "medium", "high", "critical"}


def test_alert_statuses_include_required_values() -> None:
    assert set(ALERT_STATUSES) == {
        "New",
        "In review",
        "Escalated",
        "Information requested",
        "Closed false positive",
        "Closed suspicious",
        "Archived",
    }


def test_create_alert_record_returns_alert_record() -> None:
    assert isinstance(_alert(), AlertRecord)


def test_alert_creation_normalises_severity_to_lowercase() -> None:
    assert _alert().severity == "high"


def test_alert_creation_converts_evidence_ids_to_tuple() -> None:
    assert _alert().evidence_ids == ("TXN_001", "TXN_002")


def test_alert_creation_fills_created_and_updated_timestamps() -> None:
    alert = _alert()

    assert alert.created_at is not None
    assert alert.updated_at is not None


def test_alert_record_to_dict_returns_json_serialisable_dictionary() -> None:
    payload = alert_record_to_dict(_alert())

    json.dumps(payload, sort_keys=True)
    assert payload["evidence_ids"] == ["TXN_001", "TXN_002"]


def test_alert_record_from_dict_reconstructs_valid_alert() -> None:
    reconstructed = alert_record_from_dict(alert_record_to_dict(_alert()))

    assert reconstructed.alert_id == "AL_STRUCTURING_001"
    assert reconstructed.reason_code == "STRUCTURING_THRESHOLD"


def test_invalid_severity_raises_alert_validation_error() -> None:
    with pytest.raises(AlertValidationError):
        create_alert_record(
            "AL_001",
            "ACC_001",
            None,
            "Rule",
            "typology",
            "urgent",
            50,
            "REASON",
            ["TXN_001"],
            None,
            None,
        )


def test_invalid_risk_score_raises_alert_validation_error() -> None:
    with pytest.raises(AlertValidationError):
        create_alert_record(
            "AL_001",
            "ACC_001",
            None,
            "Rule",
            "typology",
            "high",
            101,
            "REASON",
            ["TXN_001"],
            None,
            None,
        )


def test_empty_evidence_ids_raise_alert_validation_error() -> None:
    with pytest.raises(AlertValidationError):
        create_alert_record(
            "AL_001",
            "ACC_001",
            None,
            "Rule",
            "typology",
            "high",
            50,
            "REASON",
            [],
            None,
            None,
        )


def test_invalid_detection_window_ordering_raises_alert_validation_error() -> None:
    with pytest.raises(AlertValidationError):
        create_alert_record(
            "AL_001",
            "ACC_001",
            None,
            "Rule",
            "typology",
            "high",
            50,
            "REASON",
            ["TXN_001"],
            "2025-01-02T00:00:00Z",
            "2025-01-01T00:00:00Z",
        )
