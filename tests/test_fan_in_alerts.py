"""Tests for fan-in detection to alert conversion."""

import pandas as pd

from graph_aml.alerts import AlertRecord, validate_alert_records
from graph_aml.rules import FanInRuleConfig, build_fan_in_alerts, detect_fan_in_windows
from tests.fixtures.fan_in_fixtures import (
    build_fan_in_accounts_fixture,
    build_fan_in_trigger_transactions_fixture,
)


def _detections(count: int = 15) -> pd.DataFrame:
    return detect_fan_in_windows(
        build_fan_in_trigger_transactions_fixture(unique_sender_count=count)
    )


def test_build_fan_in_alerts_returns_alert_records() -> None:
    alerts = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())

    assert isinstance(alerts[0], AlertRecord)


def test_alert_rule_name_is_fan_in() -> None:
    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())[0]

    assert alert.rule_name == "Fan-in"


def test_alert_typology_is_fan_in() -> None:
    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())[0]

    assert alert.typology == "fan_in"


def test_alert_severity_matches_config() -> None:
    config = FanInRuleConfig(severity="critical")

    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture(), config)[0]

    assert alert.severity == "critical"


def test_risk_score_uses_base_score_for_normal_detections() -> None:
    config = FanInRuleConfig(high_sender_multiplier=2.0)

    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture(), config)[0]

    assert alert.risk_score_rule == 80.0


def test_risk_score_uses_high_sender_score_for_high_sender_detections() -> None:
    config = FanInRuleConfig(min_unique_senders=15, high_sender_multiplier=1.0)

    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture(), config)[0]

    assert alert.risk_score_rule == 90.0


def test_reason_code_includes_unique_sender_count_and_window() -> None:
    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())[0]

    assert alert.reason_code == "15 unique senders within 7 days"


def test_evidence_ids_are_preserved() -> None:
    detection = _detections()
    alert = build_fan_in_alerts(detection, build_fan_in_accounts_fixture())[0]

    assert alert.evidence_ids == detection.loc[0, "evidence_ids"]


def test_customer_id_is_attached_from_accounts() -> None:
    alert = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())[0]

    assert alert.customer_id == "CUST_COLLECT_001"


def test_alert_ids_are_deterministic() -> None:
    first = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())
    second = build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture())

    assert first[0].alert_id == second[0].alert_id


def test_alerts_validate_through_common_alert_validation() -> None:
    validate_alert_records(build_fan_in_alerts(_detections(), build_fan_in_accounts_fixture()))
