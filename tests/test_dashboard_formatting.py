"""Tests for dashboard formatting helpers."""

import pandas as pd

from graph_aml.dashboard.formatting import (
    dataframe_for_display,
    format_amount,
    format_case_status,
    format_risk_band,
    format_score,
    format_timestamp,
)


def test_score_formatting_handles_numeric_and_missing_values() -> None:
    assert format_score(12.3456) == "12.35"
    assert format_score(None) == "-"


def test_amount_formatting_includes_currency() -> None:
    assert format_amount("1234.5", currency="USD") == "USD 1,234.50"


def test_timestamp_formatting_is_deterministic() -> None:
    assert format_timestamp("2026-05-12T01:02:03") == "2026-05-12 01:02:03"


def test_risk_band_and_status_formatting_are_stable() -> None:
    assert format_risk_band("critical") == "Critical"
    assert format_case_status("In review") == "In review"


def test_dataframe_for_display_compacts_json_without_mutating() -> None:
    frame = pd.DataFrame({"payload": [{"b": 2, "a": 1}]})
    original = frame.copy(deep=True)

    display = dataframe_for_display(frame)

    assert display.loc[0, "payload"] == '{"a": 1, "b": 2}'
    assert isinstance(frame.loc[0, "payload"], dict)
    pd.testing.assert_frame_equal(frame, original)
