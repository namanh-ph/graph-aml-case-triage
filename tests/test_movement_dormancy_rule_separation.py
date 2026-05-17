"""Cross-rule separation tests for rapid movement and dormant reactivation."""

from graph_aml.rules import (
    detect_dormant_reactivation_windows,
    detect_rapid_movement_windows,
    run_dormant_reactivation_rule,
    run_rapid_movement_rule,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_cross_rule_benign_transactions_fixture,
    build_dormant_reactivation_only_transactions_fixture,
    build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_rapid_only_fixture_produces_rapid_alerts() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )

    assert alerts


def test_rapid_only_fixture_does_not_produce_dormant_alerts() -> None:
    alerts = run_dormant_reactivation_rule(
        build_rapid_movement_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )

    assert alerts == ()


def test_dormant_only_fixture_produces_dormant_alerts() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )

    assert alerts


def test_dormant_only_fixture_does_not_produce_rapid_alerts() -> None:
    alerts = run_rapid_movement_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        build_movement_dormancy_accounts_fixture(),
    )

    assert alerts == ()


def test_cross_rule_benign_fixture_produces_no_alerts() -> None:
    transactions = build_cross_rule_benign_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()

    assert run_rapid_movement_rule(transactions, accounts) == ()
    assert run_dormant_reactivation_rule(transactions, accounts) == ()


def test_pass_through_behavior_is_interpreted_by_rapid_movement() -> None:
    detections = detect_rapid_movement_windows(build_rapid_movement_only_transactions_fixture())

    assert detections.loc[0, "account_id"] == "ACC_PASS_001"
    assert detections.loc[0, "outflow_ratio"] == 0.9


def test_long_inactivity_is_interpreted_by_dormant_reactivation() -> None:
    detections = detect_dormant_reactivation_windows(
        build_dormant_reactivation_only_transactions_fixture()
    )

    assert detections.loc[0, "account_id"] == "ACC_DORMANT_001"
    assert detections.loc[0, "dormant_days_before_activity"] >= 120


def test_rule_outputs_remain_independent_on_same_fixture() -> None:
    transactions = build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()

    rapid = run_rapid_movement_rule(transactions, accounts)
    dormant = run_dormant_reactivation_rule(transactions, accounts)

    assert {alert.typology for alert in rapid} == {"rapid_movement"}
    assert {alert.typology for alert in dormant} == {"dormant_reactivation"}
    assert {alert.alert_id for alert in rapid}.isdisjoint({alert.alert_id for alert in dormant})
