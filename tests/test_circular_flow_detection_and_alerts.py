"""Tests for combined circular flow detection and alert result helper."""

import json

import pandas as pd

from graph_aml.alerts import alert_record_to_dict
from graph_aml.rules import (
    circular_flow_detections_to_dicts,
    run_circular_flow_detection_and_alerts,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_accounts_fixture,
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
)


def test_detection_and_alerts_result_contains_expected_keys() -> None:
    result = run_circular_flow_detection_and_alerts(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert isinstance(result, dict)
    assert {"detections", "alerts", "detection_summary", "alert_summary"} <= set(result)


def test_detection_and_alerts_reuses_detection_output_for_alerts() -> None:
    result = run_circular_flow_detection_and_alerts(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )
    detections = result["detections"]
    alerts = result["alerts"]

    assert isinstance(detections, pd.DataFrame)
    assert alerts[0].evidence_ids == detections.loc[0, "evidence_ids"]


def test_alert_summary_count_matches_number_of_alerts() -> None:
    result = run_circular_flow_detection_and_alerts(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert result["alert_summary"]["alert_count"] == len(result["alerts"])


def test_empty_inputs_are_handled_gracefully() -> None:
    result = run_circular_flow_detection_and_alerts(
        build_circular_flow_non_trigger_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )

    assert result["detections"].empty
    assert result["alerts"] == ()
    assert result["detection_summary"]["cycle_count"] == 0
    assert result["alert_summary"]["alert_count"] == 0


def test_outputs_are_json_serialisable_where_applicable() -> None:
    result = run_circular_flow_detection_and_alerts(
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )
    payload = {
        "detections": circular_flow_detections_to_dicts(result["detections"]),
        "alerts": [alert_record_to_dict(alert) for alert in result["alerts"]],
        "detection_summary": result["detection_summary"],
        "alert_summary": result["alert_summary"],
    }

    json.dumps(payload, default=str)
