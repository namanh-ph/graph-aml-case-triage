"""Tests for dormant reactivation detection to alert conversion."""

from graph_aml.alerts import AlertRecord, validate_alert_records
from graph_aml.rules import (
    DormantReactivationRuleConfig,
    build_dormant_reactivation_alerts,
    detect_dormant_reactivation_windows,
)
from tests.fixtures.dormant_reactivation_fixtures import (
    build_dormant_reactivation_accounts_fixture,
    build_dormant_reactivation_trigger_transactions_fixture,
)


def _detections(outbound_amount: float = 10000.0):
    return detect_dormant_reactivation_windows(
        build_dormant_reactivation_trigger_transactions_fixture(outbound_amount=outbound_amount)
    )


def test_build_dormant_reactivation_alerts_returns_alert_records() -> None:
    alerts = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert isinstance(alerts[0], AlertRecord)


def test_alert_rule_name_is_dormant_reactivation() -> None:
    alert = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.rule_name == "Dormant reactivation"


def test_alert_typology_is_dormant_reactivation() -> None:
    alert = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.typology == "dormant_reactivation"


def test_alert_severity_matches_config() -> None:
    config = DormantReactivationRuleConfig(severity="critical")

    alert = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
        config,
    )[0]

    assert alert.severity == "critical"


def test_risk_score_uses_base_score_for_normal_detection() -> None:
    alert = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 80.0


def test_risk_score_uses_high_value_score_for_high_value_detection() -> None:
    alert = build_dormant_reactivation_alerts(
        _detections(outbound_amount=20000.0),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.risk_score_rule == 90.0


def test_reason_code_includes_dormant_days_outbound_value_and_window() -> None:
    alert = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.reason_code == (
        "131 inactive days followed by 10000.00 outbound value within 7 days"
    )


def test_evidence_ids_are_preserved() -> None:
    detection = _detections()
    alert = build_dormant_reactivation_alerts(
        detection,
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.evidence_ids == detection.loc[0, "evidence_ids"]


def test_customer_id_is_attached_from_accounts() -> None:
    alert = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.customer_id == "CUST_DORMANT_001"


def test_alert_ids_are_deterministic() -> None:
    first = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )
    second = build_dormant_reactivation_alerts(
        _detections(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert first[0].alert_id == second[0].alert_id


def test_alerts_validate_through_common_alert_validation() -> None:
    validate_alert_records(
        build_dormant_reactivation_alerts(
            _detections(),
            build_dormant_reactivation_accounts_fixture(),
        )
    )
