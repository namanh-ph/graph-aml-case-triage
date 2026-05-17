"""Tests for alert validation utilities."""

from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.alerts import (
    AlertRecord,
    AlertValidationError,
    alerts_to_dataframe,
    create_alert_record,
    validate_alert_dataframe,
    validate_alert_record,
    validate_alert_records,
)


def _alert(alert_id: str = "AL_001") -> AlertRecord:
    return create_alert_record(
        alert_id,
        "ACC_001",
        "CUST_001",
        "Structuring",
        "structuring",
        "high",
        80,
        "STRUCTURING_THRESHOLD",
        ["TXN_001"],
        "2025-01-01T00:00:00Z",
        "2025-01-02T00:00:00Z",
    )


def test_validate_alert_record_passes_valid_alerts() -> None:
    validate_alert_record(_alert())


def test_validate_alert_records_passes_list_of_valid_alerts() -> None:
    validate_alert_records([_alert("AL_001"), _alert("AL_002")])


def test_validate_alert_records_fails_when_any_alert_is_invalid() -> None:
    alert = _alert()
    object.__setattr__(alert, "severity", "urgent")

    with pytest.raises(AlertValidationError):
        validate_alert_records([alert])


def test_validate_alert_dataframe_passes_valid_alert_dataframe() -> None:
    validate_alert_dataframe(alerts_to_dataframe([_alert()]))


def test_validate_alert_dataframe_fails_when_required_columns_are_missing() -> None:
    frame = alerts_to_dataframe([_alert()]).drop(columns=["alert_id"])

    with pytest.raises(AlertValidationError):
        validate_alert_dataframe(frame)


def test_validate_alert_dataframe_fails_on_duplicate_alert_ids() -> None:
    frame = pd.concat([alerts_to_dataframe([_alert()]), alerts_to_dataframe([_alert()])])

    with pytest.raises(AlertValidationError):
        validate_alert_dataframe(frame)


def test_validate_alert_dataframe_fails_on_invalid_severity() -> None:
    frame = alerts_to_dataframe([_alert()])
    frame.loc[0, "severity"] = "urgent"

    with pytest.raises(AlertValidationError):
        validate_alert_dataframe(frame)


def test_validate_alert_dataframe_fails_on_invalid_status() -> None:
    frame = alerts_to_dataframe([_alert()])
    frame.loc[0, "alert_status"] = "Unknown"

    with pytest.raises(AlertValidationError):
        validate_alert_dataframe(frame)


def test_validate_alert_dataframe_fails_on_risk_scores_outside_range() -> None:
    frame = alerts_to_dataframe([_alert()])
    frame.loc[0, "risk_score_rule"] = -1

    with pytest.raises(AlertValidationError):
        validate_alert_dataframe(frame)


def test_validate_alert_dataframe_fails_on_empty_evidence_ids() -> None:
    frame = alerts_to_dataframe([_alert()])
    frame.at[0, "evidence_ids"] = []

    with pytest.raises(AlertValidationError):
        validate_alert_dataframe(frame)
