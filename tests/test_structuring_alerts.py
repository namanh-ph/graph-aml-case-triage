"""Tests for structuring detection to alert conversion."""

import pandas as pd

from graph_aml.alerts import AlertRecord, validate_alert_records
from graph_aml.rules import StructuringRuleConfig, build_structuring_alerts


def _detections(count: int = 8) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "account_id": "ACC_1",
                "detection_window_start": "2025-01-01T00:00:00+00:00",
                "detection_window_end": "2025-01-01T07:00:00+00:00",
                "transaction_count": count,
                "total_amount": float(count * 9500),
                "min_amount": 9500.0,
                "max_amount": 9500.0,
                "evidence_ids": tuple(f"TXN_{idx}" for idx in range(count)),
            }
        ]
    )


def _accounts() -> pd.DataFrame:
    return pd.DataFrame({"account_id": ["ACC_1"], "customer_id": ["CUST_1"]})


def test_build_structuring_alerts_returns_alert_records() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    assert isinstance(alerts[0], AlertRecord)


def test_alert_rule_name_is_structuring() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    assert alerts[0].rule_name == "Structuring"


def test_alert_typology_is_structuring() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    assert alerts[0].typology == "structuring"


def test_alert_severity_matches_config() -> None:
    config = StructuringRuleConfig(severity="critical")

    alerts = build_structuring_alerts(_detections(), _accounts(), config)

    assert alerts[0].severity == "critical"


def test_risk_score_uses_base_score_for_normal_detections() -> None:
    config = StructuringRuleConfig(min_transaction_count=8, high_count_multiplier=2.0)

    alerts = build_structuring_alerts(_detections(8), _accounts(), config)

    assert alerts[0].risk_score_rule == 80.0


def test_risk_score_uses_high_count_score_for_high_count_detections() -> None:
    config = StructuringRuleConfig(min_transaction_count=8, high_count_multiplier=1.5)

    alerts = build_structuring_alerts(_detections(12), _accounts(), config)

    assert alerts[0].risk_score_rule == 90.0


def test_reason_code_includes_transaction_count_and_window() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    assert alerts[0].reason_code == "8 transfers below threshold within 24 hours"


def test_evidence_ids_are_preserved() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    assert alerts[0].evidence_ids[0] == "TXN_0"


def test_customer_id_is_attached_from_accounts() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    assert alerts[0].customer_id == "CUST_1"


def test_alert_ids_are_deterministic() -> None:
    first = build_structuring_alerts(_detections(), _accounts())
    second = build_structuring_alerts(_detections(), _accounts())

    assert first[0].alert_id == second[0].alert_id


def test_alerts_validate_through_common_alert_validation() -> None:
    alerts = build_structuring_alerts(_detections(), _accounts())

    validate_alert_records(alerts)
