"""Deterministic alert ID regression tests for movement and dormancy rules."""

import pandas as pd

from graph_aml.rules import run_dormant_reactivation_rule, run_rapid_movement_rule
from tests.fixtures.movement_dormancy_fixtures import (
    build_dormant_reactivation_only_transactions_fixture,
    build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
    build_rapid_movement_only_transactions_fixture,
)


def test_running_rapid_on_same_fixture_twice_produces_same_alert_ids() -> None:
    accounts = build_movement_dormancy_accounts_fixture()

    first = run_rapid_movement_rule(build_rapid_movement_only_transactions_fixture(), accounts)
    second = run_rapid_movement_rule(build_rapid_movement_only_transactions_fixture(), accounts)

    assert [alert.alert_id for alert in first] == [alert.alert_id for alert in second]


def test_running_dormant_on_same_fixture_twice_produces_same_alert_ids() -> None:
    accounts = build_movement_dormancy_accounts_fixture()

    first = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        accounts,
    )
    second = run_dormant_reactivation_rule(
        build_dormant_reactivation_only_transactions_fixture(),
        accounts,
    )

    assert [alert.alert_id for alert in first] == [alert.alert_id for alert in second]


def test_reordering_rapid_input_transactions_does_not_change_ids() -> None:
    frame = build_rapid_movement_only_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()

    first = run_rapid_movement_rule(frame, accounts)
    second = run_rapid_movement_rule(frame.iloc[::-1], accounts)

    assert first[0].alert_id == second[0].alert_id


def test_reordering_dormant_input_transactions_does_not_change_ids() -> None:
    frame = build_dormant_reactivation_only_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()

    first = run_dormant_reactivation_rule(frame, accounts)
    second = run_dormant_reactivation_rule(frame.iloc[::-1], accounts)

    assert first[0].alert_id == second[0].alert_id


def test_changing_rapid_pass_through_account_changes_alert_id() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    original = build_rapid_movement_only_transactions_fixture()
    changed = original.replace("ACC_PASS_001", "ACC_PASS_002")

    assert (
        run_rapid_movement_rule(original, accounts)[0].alert_id
        != run_rapid_movement_rule(
            changed,
            accounts,
        )[0].alert_id
    )


def test_changing_dormant_reactivation_account_changes_alert_id() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    original = build_dormant_reactivation_only_transactions_fixture()
    changed = original.replace("ACC_DORMANT_001", "ACC_DORMANT_002")

    assert (
        run_dormant_reactivation_rule(
            original,
            accounts,
        )[0].alert_id
        != run_dormant_reactivation_rule(changed, accounts)[0].alert_id
    )


def test_changing_rapid_detection_window_changes_alert_id() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    original = build_rapid_movement_only_transactions_fixture()
    changed = original.copy(deep=True)
    changed["transaction_timestamp"] = pd.to_datetime(
        changed["transaction_timestamp"],
        utc=True,
    ) + pd.Timedelta(days=1)

    assert (
        run_rapid_movement_rule(original, accounts)[0].alert_id
        != run_rapid_movement_rule(
            changed,
            accounts,
        )[0].alert_id
    )


def test_changing_dormant_detection_window_changes_alert_id() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    original = build_dormant_reactivation_only_transactions_fixture()
    changed = original.copy(deep=True)
    changed.loc[changed["transaction_id"].str.contains("REACT"), "transaction_timestamp"] = (
        pd.Timestamp("2025-01-11 09:00:00", tz="UTC")
    )

    assert (
        run_dormant_reactivation_rule(
            original,
            accounts,
        )[0].alert_id
        != run_dormant_reactivation_rule(changed, accounts)[0].alert_id
    )


def test_changing_rapid_evidence_transactions_changes_alert_id() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    original = build_rapid_movement_only_transactions_fixture()
    changed = original.copy(deep=True)
    changed.loc[changed["transaction_id"].str.contains("OUT"), "transaction_id"] = (
        "TXN_MD_RM_ONLY_OUT_CHANGED"
    )

    assert (
        run_rapid_movement_rule(original, accounts)[0].alert_id
        != run_rapid_movement_rule(
            changed,
            accounts,
        )[0].alert_id
    )


def test_changing_dormant_evidence_transactions_changes_alert_id() -> None:
    accounts = build_movement_dormancy_accounts_fixture()
    original = build_dormant_reactivation_only_transactions_fixture()
    changed = original.copy(deep=True)
    changed.loc[changed["transaction_id"].str.contains("REACT"), "transaction_id"] = (
        "TXN_MD_DR_ONLY_REACT_CHANGED"
    )

    assert (
        run_dormant_reactivation_rule(
            original,
            accounts,
        )[0].alert_id
        != run_dormant_reactivation_rule(changed, accounts)[0].alert_id
    )


def test_rapid_and_dormant_alert_ids_do_not_collide_on_same_fixture() -> None:
    transactions = build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
    accounts = build_movement_dormancy_accounts_fixture()
    rapid = run_rapid_movement_rule(transactions, accounts)
    dormant = run_dormant_reactivation_rule(transactions, accounts)

    assert {alert.alert_id for alert in rapid}.isdisjoint({alert.alert_id for alert in dormant})
