"""Tests for alert DataFrame conversion utilities."""

from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.alerts import (
    ALERT_COLUMNS,
    AlertDataFrameError,
    alerts_to_dataframe,
    create_alert_record,
    dataframe_to_alerts,
    normalise_alert_dataframe,
)


def _alerts():
    return [
        create_alert_record(
            "AL_002",
            "ACC_002",
            "CUST_002",
            "Fan In",
            "fan_in",
            "medium",
            60,
            "FAN_IN",
            ["TXN_002"],
            "2025-01-02T00:00:00Z",
            "2025-01-03T00:00:00Z",
        ),
        create_alert_record(
            "AL_001",
            "ACC_001",
            "CUST_001",
            "Structuring",
            "structuring",
            "high",
            80,
            "STRUCTURING",
            ["TXN_001"],
            "2025-01-01T00:00:00Z",
            "2025-01-02T00:00:00Z",
        ),
    ]


def test_alerts_to_dataframe_returns_alert_columns() -> None:
    assert tuple(alerts_to_dataframe(_alerts()).columns) == ALERT_COLUMNS


def test_alert_dataframe_preserves_evidence_ids() -> None:
    frame = alerts_to_dataframe(_alerts())

    assert frame.loc[0, "evidence_ids"] == ["TXN_001"]


def test_dataframe_to_alerts_reconstructs_records() -> None:
    records = dataframe_to_alerts(alerts_to_dataframe(_alerts()))

    assert len(records) == 2
    assert records[0].alert_id == "AL_001"


def test_round_trip_preserves_alert_ids_and_reason_codes() -> None:
    records = dataframe_to_alerts(alerts_to_dataframe(_alerts()))

    assert [record.alert_id for record in records] == ["AL_001", "AL_002"]
    assert [record.reason_code for record in records] == ["STRUCTURING", "FAN_IN"]


def test_normalise_alert_dataframe_fills_missing_status_with_new() -> None:
    frame = alerts_to_dataframe([_alerts()[0]]).drop(columns=["alert_status"])

    assert normalise_alert_dataframe(frame).loc[0, "alert_status"] == "New"


def test_normalise_alert_dataframe_fills_missing_timestamps() -> None:
    frame = alerts_to_dataframe([_alerts()[0]]).drop(columns=["created_at", "updated_at"])
    normalised = normalise_alert_dataframe(frame)

    assert pd.notna(normalised.loc[0, "created_at"])
    assert pd.notna(normalised.loc[0, "updated_at"])


def test_normalised_dataframe_is_sorted_deterministically() -> None:
    frame = alerts_to_dataframe(_alerts()).sort_values("alert_id", ascending=False)

    assert list(normalise_alert_dataframe(frame)["alert_id"]) == ["AL_001", "AL_002"]


def test_input_dataframes_are_not_mutated() -> None:
    frame = alerts_to_dataframe([_alerts()[0]]).drop(columns=["alert_status"])
    original = frame.copy(deep=True)

    normalise_alert_dataframe(frame)

    pd.testing.assert_frame_equal(frame, original)


def test_conversion_failures_raise_alert_dataframe_error() -> None:
    frame = alerts_to_dataframe([_alerts()[0]])
    frame.at[0, "evidence_ids"] = []

    with pytest.raises(AlertDataFrameError):
        dataframe_to_alerts(frame)
