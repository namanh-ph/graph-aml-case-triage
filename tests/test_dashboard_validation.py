"""Tests for dashboard validation helpers."""

import json

import pandas as pd
import pytest

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.validation import (
    build_dashboard_data_quality_summary,
    validate_dashboard_alert_queue,
    validate_dashboard_case_detail,
    validate_dashboard_case_queue,
)


def test_valid_dashboard_frames_pass_validation() -> None:
    validate_dashboard_alert_queue(pd.DataFrame({"alert_id": ["A1"], "severity": ["high"]}))
    validate_dashboard_case_queue(pd.DataFrame({"case_id": ["C1"], "status": ["New"]}))
    validate_dashboard_case_detail(
        {
            "case": pd.DataFrame({"case_id": ["C1"]}),
            "case_risk_scores": pd.DataFrame(),
            "case_alerts": pd.DataFrame(),
            "alerts": pd.DataFrame(),
            "case_entities": pd.DataFrame(),
            "lifecycle_events": pd.DataFrame(),
        }
    )


def test_malformed_dashboard_frames_raise() -> None:
    with pytest.raises(DashboardDataError):
        validate_dashboard_alert_queue(pd.DataFrame({"severity": ["high"]}))
    with pytest.raises(DashboardDataError):
        validate_dashboard_case_queue(pd.DataFrame({"status": ["New"]}))
    with pytest.raises(DashboardDataError):
        validate_dashboard_case_detail({"case": pd.DataFrame()})


def test_quality_summary_is_json_serialisable_and_empty_safe() -> None:
    summary = build_dashboard_data_quality_summary({}, pd.DataFrame(), pd.DataFrame())

    assert summary["case_queue_rows"] == 0
    json.dumps(summary, sort_keys=True)
