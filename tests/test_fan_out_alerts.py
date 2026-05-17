"""Tests for fan-out detection to alert conversion."""

import pandas as pd

from graph_aml.alerts import AlertRecord, validate_alert_records
from graph_aml.rules import FanOutRuleConfig, build_fan_out_alerts, detect_fan_out_windows
from tests.fixtures.fan_out_fixtures import (
    build_fan_out_accounts_fixture,
    build_fan_out_trigger_transactions_fixture,
)


def _detections(count: int = 20) -> pd.DataFrame:
    return detect_fan_out_windows(
        build_fan_out_trigger_transactions_fixture(unique_recipient_count=count)
    )


def test_build_fan_out_alerts_returns_alert_records() -> None:
    alerts = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())

    assert isinstance(alerts[0], AlertRecord)


def test_alert_rule_name_is_fan_out() -> None:
    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())[0]

    assert alert.rule_name == "Fan-out"


def test_alert_typology_is_fan_out() -> None:
    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())[0]

    assert alert.typology == "fan_out"


def test_alert_severity_matches_config() -> None:
    config = FanOutRuleConfig(severity="critical")

    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture(), config)[0]

    assert alert.severity == "critical"


def test_risk_score_uses_base_score_for_normal_detections() -> None:
    config = FanOutRuleConfig(high_recipient_multiplier=2.0)

    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture(), config)[0]

    assert alert.risk_score_rule == 80.0


def test_risk_score_uses_high_recipient_score_for_high_recipient_detections() -> None:
    config = FanOutRuleConfig(min_unique_recipients=20, high_recipient_multiplier=1.0)

    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture(), config)[0]

    assert alert.risk_score_rule == 90.0


def test_reason_code_includes_unique_recipient_count_and_window() -> None:
    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())[0]

    assert alert.reason_code == "20 unique recipients within 7 days"


def test_evidence_ids_are_preserved() -> None:
    detection = _detections()
    alert = build_fan_out_alerts(detection, build_fan_out_accounts_fixture())[0]

    assert alert.evidence_ids == detection.loc[0, "evidence_ids"]


def test_customer_id_is_attached_from_accounts() -> None:
    alert = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())[0]

    assert alert.customer_id == "CUST_DISPERSE_001"


def test_alert_ids_are_deterministic() -> None:
    first = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())
    second = build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture())

    assert first[0].alert_id == second[0].alert_id


def test_alerts_validate_through_common_alert_validation() -> None:
    validate_alert_records(build_fan_out_alerts(_detections(), build_fan_out_accounts_fixture()))
