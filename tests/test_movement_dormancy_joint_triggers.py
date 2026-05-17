"""Joint trigger tests for rapid movement and dormant reactivation."""

from graph_aml.alerts import validate_alert_record
from graph_aml.rules import run_dormant_reactivation_rule, run_rapid_movement_rule
from tests.fixtures.movement_dormancy_fixtures import (
    build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
)


def _alerts():
    transactions = build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()
    return (
        run_rapid_movement_rule(transactions, accounts),
        run_dormant_reactivation_rule(transactions, accounts),
    )


def test_joint_fixture_produces_both_rule_alerts() -> None:
    rapid_alerts, dormant_alerts = _alerts()

    assert rapid_alerts
    assert dormant_alerts


def test_rapid_movement_alerts_use_pass_through_account_ids() -> None:
    rapid_alerts, _ = _alerts()

    assert {alert.account_id for alert in rapid_alerts} == {"ACC_PASS_001"}


def test_dormant_alerts_use_reactivated_account_ids() -> None:
    _, dormant_alerts = _alerts()

    assert {alert.account_id for alert in dormant_alerts} == {"ACC_DORMANT_001"}


def test_alert_typologies_are_rule_specific() -> None:
    rapid_alerts, dormant_alerts = _alerts()

    assert rapid_alerts[0].typology == "rapid_movement"
    assert dormant_alerts[0].typology == "dormant_reactivation"


def test_alert_rule_names_are_rule_specific() -> None:
    rapid_alerts, dormant_alerts = _alerts()

    assert rapid_alerts[0].rule_name == "Rapid movement"
    assert dormant_alerts[0].rule_name == "Dormant reactivation"


def test_customer_ids_are_attached_for_each_rule() -> None:
    rapid_alerts, dormant_alerts = _alerts()

    assert rapid_alerts[0].customer_id == "CUST_PASS_001"
    assert dormant_alerts[0].customer_id == "CUST_DORMANT_001"


def test_joint_alerts_validate_through_common_schema() -> None:
    rapid_alerts, dormant_alerts = _alerts()

    for alert in (*rapid_alerts, *dormant_alerts):
        validate_alert_record(alert)
