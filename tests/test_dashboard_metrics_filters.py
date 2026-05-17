"""Tests for dashboard metrics and filters."""

import pandas as pd
import pytest

from graph_aml.dashboard.config import DashboardConfig
from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.filters import (
    apply_dataframe_search_filter,
    get_default_alert_severity_filter,
    get_default_case_status_filter,
    get_default_risk_band_filter,
    normalise_filter_values,
)
from graph_aml.dashboard.metrics import (
    build_alert_queue_metrics,
    build_case_detail_metrics,
    build_case_queue_metrics,
    build_overview_metric_cards,
)


def test_metric_helpers_build_expected_payloads() -> None:
    overview = build_overview_metric_cards({"transaction_count": 2, "account_count": 1})
    cases = pd.DataFrame(
        {"status": ["New", "Closed suspicious"], "risk_band": ["critical", "high"]}
    )
    alerts = pd.DataFrame({"severity": ["critical", "low"], "typology": ["fan-in", "fan-out"]})
    detail = {
        "alerts": alerts,
        "case_entities": pd.DataFrame({"x": [1]}),
        "lifecycle_events": pd.DataFrame({"x": [1]}),
        "case": cases,
        "case_risk_scores": cases,
    }

    assert overview[0]["value"] == 2
    assert build_case_queue_metrics(cases)["critical_case_count"] == 1
    assert build_alert_queue_metrics(alerts)["critical_alert_count"] == 1
    assert build_case_detail_metrics(detail)["linked_alert_count"] == 2


def test_filter_helpers_normalise_and_search_without_mutation() -> None:
    frame = pd.DataFrame({"case_id": ["CASE1", "CASE2"], "account_id": ["ACC1", "B"]})
    original = frame.copy(deep=True)

    assert normalise_filter_values(" high ") == ("high",)
    assert normalise_filter_values(["a", "a", "b"]) == ("a", "b")
    filtered = apply_dataframe_search_filter(frame, "acc", ["account_id"])

    assert filtered["case_id"].tolist() == ["CASE1"]
    pd.testing.assert_frame_equal(frame, original)


def test_default_filters_come_from_config() -> None:
    config = DashboardConfig(
        default_case_statuses=("New",),
        default_risk_bands=("critical",),
        default_alert_severities=("high",),
    )

    assert get_default_case_status_filter(config) == ("New",)
    assert get_default_risk_band_filter(config) == ("critical",)
    assert get_default_alert_severity_filter(config) == ("high",)


def test_malformed_metric_and_filter_inputs_raise() -> None:
    with pytest.raises(DashboardDataError):
        build_case_queue_metrics({"bad": "input"})  # type: ignore[arg-type]
    with pytest.raises(DashboardDataError):
        apply_dataframe_search_filter({"bad": "input"}, "x", ["x"])  # type: ignore[arg-type]
