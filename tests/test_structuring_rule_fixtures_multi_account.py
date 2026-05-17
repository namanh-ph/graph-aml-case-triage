"""Fixture-based multi-account tests for structuring detection."""

from graph_aml.rules import run_structuring_rule, summarise_rule_alerts
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_multi_account_transactions_fixture,
)


def _alerts():
    return run_structuring_rule(
        build_structuring_multi_account_transactions_fixture(),
        build_structuring_accounts_fixture(),
    )


def test_multiple_triggering_accounts_produce_multiple_alerts() -> None:
    assert len(_alerts()) == 2


def test_non_triggering_accounts_are_excluded() -> None:
    assert "ACC_BENIGN_001" not in {alert.account_id for alert in _alerts()}


def test_alert_ids_are_unique_across_accounts() -> None:
    alert_ids = [alert.alert_id for alert in _alerts()]

    assert len(alert_ids) == len(set(alert_ids))


def test_evidence_ids_do_not_leak_across_accounts() -> None:
    for alert in _alerts():
        expected_marker = "_A_" if alert.account_id == "ACC_STRUCT_001" else "_B_"
        assert all(expected_marker in evidence_id for evidence_id in alert.evidence_ids)


def test_customer_ids_are_attached_correctly_per_account() -> None:
    customer_by_account = {alert.account_id: alert.customer_id for alert in _alerts()}

    assert customer_by_account == {
        "ACC_STRUCT_001": "CUST_STRUCT_001",
        "ACC_STRUCT_002": "CUST_STRUCT_002",
    }


def test_alerts_are_sorted_deterministically() -> None:
    alerts = _alerts()

    assert [alert.account_id for alert in alerts] == ["ACC_STRUCT_001", "ACC_STRUCT_002"]


def test_identical_patterns_for_different_accounts_produce_distinct_alert_ids() -> None:
    alerts = _alerts()

    assert alerts[0].alert_id != alerts[1].alert_id


def test_mixed_trigger_and_benign_activity_is_handled_correctly() -> None:
    summary = summarise_rule_alerts(_alerts())

    assert summary["alert_count"] == 2
    assert summary["unique_account_count"] == 2


def test_detection_summary_counts_match_triggering_accounts() -> None:
    summary = summarise_rule_alerts(_alerts())

    assert summary["rule_name_counts"] == {"Structuring": 2}
