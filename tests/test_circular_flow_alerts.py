"""Tests for circular flow alert construction."""

import pandas as pd

from graph_aml.alerts import AlertRecord, validate_alert_records
from graph_aml.rules import (
    CircularFlowRuleConfig,
    build_circular_flow_alerts,
    detect_circular_flows,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_accounts_fixture,
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_two_hop_transactions_fixture,
)


def _detections() -> pd.DataFrame:
    return detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())


def test_build_circular_flow_alerts_returns_alert_records() -> None:
    alerts = build_circular_flow_alerts(_detections(), build_circular_flow_accounts_fixture())

    assert isinstance(alerts[0], AlertRecord)


def test_empty_detections_return_empty_tuple() -> None:
    detections = detect_circular_flows(build_circular_flow_non_trigger_transactions_fixture())

    alerts = build_circular_flow_alerts(detections, build_circular_flow_accounts_fixture())

    assert alerts == ()


def test_alert_core_fields_match_config_and_detection() -> None:
    config = CircularFlowRuleConfig(severity="critical")
    detections = _detections()

    alert = build_circular_flow_alerts(
        detections,
        build_circular_flow_accounts_fixture(),
        config,
    )[0]

    assert alert.rule_name == "Circular flow"
    assert alert.typology == "circular_flow"
    assert alert.severity == "critical"
    assert alert.account_id == detections.loc[0, "primary_account_id"]
    assert alert.customer_id == "CUST_CF_A"


def test_risk_score_uses_scoring_helper() -> None:
    alert = build_circular_flow_alerts(
        _detections(),
        build_circular_flow_accounts_fixture(),
        CircularFlowRuleConfig(high_amount_threshold=10000.0),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_reason_code_includes_cycle_length_and_total_amount() -> None:
    alert = build_circular_flow_alerts(_detections(), build_circular_flow_accounts_fixture())[0]

    assert "2-account circular flow" in alert.reason_code
    assert "10000.00" in alert.reason_code


def test_evidence_ids_and_detection_windows_are_preserved() -> None:
    detections = _detections()

    alert = build_circular_flow_alerts(detections, build_circular_flow_accounts_fixture())[0]

    assert alert.evidence_ids == detections.loc[0, "evidence_ids"]
    assert alert.detection_window_start is not None
    assert alert.detection_window_end is not None


def test_alert_ids_are_deterministic() -> None:
    detections = _detections()
    accounts = build_circular_flow_accounts_fixture()

    first = build_circular_flow_alerts(detections, accounts)
    second = build_circular_flow_alerts(detections, accounts)

    assert [alert.alert_id for alert in first] == [alert.alert_id for alert in second]


def test_alerts_validate_through_common_validation() -> None:
    alerts = build_circular_flow_alerts(_detections(), build_circular_flow_accounts_fixture())

    validate_alert_records(alerts)


def test_alert_construction_does_not_mutate_inputs() -> None:
    detections = _detections()
    accounts = build_circular_flow_accounts_fixture()
    original_detections = detections.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    build_circular_flow_alerts(detections, accounts)

    pd.testing.assert_frame_equal(detections, original_detections)
    pd.testing.assert_frame_equal(accounts, original_accounts)
