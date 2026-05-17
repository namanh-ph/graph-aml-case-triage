"""Tests for rapid movement detection to alert conversion."""

from graph_aml.alerts import AlertRecord, validate_alert_records
from graph_aml.rules import (
    RapidMovementRuleConfig,
    build_rapid_movement_alerts,
    detect_rapid_movement_windows,
)
from tests.fixtures.rapid_movement_fixtures import (
    build_rapid_movement_accounts_fixture,
    build_rapid_movement_trigger_transactions_fixture,
)


def _detections(sent_amount: float = 9000.0):
    return detect_rapid_movement_windows(
        build_rapid_movement_trigger_transactions_fixture(sent_amount=sent_amount)
    )


def test_build_rapid_movement_alerts_returns_alert_records() -> None:
    alerts = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())

    assert isinstance(alerts[0], AlertRecord)


def test_alert_rule_name_is_rapid_movement() -> None:
    alert = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())[0]

    assert alert.rule_name == "Rapid movement"


def test_alert_typology_is_rapid_movement() -> None:
    alert = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())[0]

    assert alert.typology == "rapid_movement"


def test_alert_severity_matches_config() -> None:
    config = RapidMovementRuleConfig(severity="critical")

    alert = build_rapid_movement_alerts(
        _detections(),
        build_rapid_movement_accounts_fixture(),
        config,
    )[0]

    assert alert.severity == "critical"


def test_risk_score_uses_base_score_for_normal_detection() -> None:
    alert = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())[0]

    assert alert.risk_score_rule == 80.0


def test_risk_score_uses_high_ratio_score_for_high_ratio_detection() -> None:
    alert = build_rapid_movement_alerts(
        _detections(sent_amount=9900.0),
        build_rapid_movement_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_reason_code_includes_outflow_percentage_and_window() -> None:
    alert = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())[0]

    assert alert.reason_code == "90 percent of received value sent out within 48 hours"


def test_evidence_ids_are_preserved() -> None:
    detection = _detections()
    alert = build_rapid_movement_alerts(detection, build_rapid_movement_accounts_fixture())[0]

    assert alert.evidence_ids == detection.loc[0, "evidence_ids"]


def test_customer_id_is_attached_from_accounts() -> None:
    alert = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())[0]

    assert alert.customer_id == "CUST_PASS_001"


def test_alert_ids_are_deterministic() -> None:
    first = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())
    second = build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())

    assert first[0].alert_id == second[0].alert_id


def test_alerts_validate_through_common_alert_validation() -> None:
    validate_alert_records(
        build_rapid_movement_alerts(_detections(), build_rapid_movement_accounts_fixture())
    )
