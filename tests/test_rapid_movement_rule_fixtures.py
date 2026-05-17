"""Focused fixture tests for the rapid movement rule."""

import pandas as pd

from graph_aml.rules import RapidMovementRuleConfig, run_rapid_movement_rule
from tests.fixtures.rapid_movement_fixtures import (
    build_rapid_movement_accounts_fixture,
    build_rapid_movement_counterparty_transactions_fixture,
    build_rapid_movement_multi_account_transactions_fixture,
    build_rapid_movement_non_trigger_transactions_fixture,
    build_rapid_movement_overlapping_window_transactions_fixture,
    build_rapid_movement_trigger_transactions_fixture,
)


def test_exact_trigger_fixture_produces_one_alert() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_incoming_funds_followed_by_sufficient_outgoing_movement_triggers() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(sent_amount=9500),
        build_rapid_movement_accounts_fixture(),
    )

    assert alerts[0].typology == "rapid_movement"


def test_insufficient_outgoing_movement_produces_no_alert() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(sent_amount=5000),
        build_rapid_movement_accounts_fixture(),
    )

    assert alerts == ()


def test_outgoing_movement_outside_window_produces_no_alert() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "transaction_timestamp"] = pd.Timestamp("2025-01-27 09:00:01", tz="UTC")

    assert run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture()) == ()


def test_total_received_below_threshold_produces_no_alert() -> None:
    config = RapidMovementRuleConfig(min_total_received=20000)

    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
        config,
    )

    assert alerts == ()


def test_retained_ratio_above_threshold_produces_no_alert() -> None:
    config = RapidMovementRuleConfig(min_outflow_ratio=0.8, max_retained_ratio=0.1)

    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(sent_amount=8500),
        build_rapid_movement_accounts_fixture(),
        config,
    )

    assert alerts == ()


def test_multiple_pass_through_accounts_produce_distinct_alerts() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_multi_account_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert len(alerts) == 2
    assert len({alert.alert_id for alert in alerts}) == 2


def test_evidence_ids_do_not_leak_across_accounts() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_multi_account_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    evidence_by_account = {alert.account_id: set(alert.evidence_ids) for alert in alerts}
    assert evidence_by_account["ACC_PASS_001"].isdisjoint(evidence_by_account["ACC_PASS_002"])


def test_customer_ids_are_attached_for_pass_through_accounts() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_multi_account_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert {alert.account_id: alert.customer_id for alert in alerts} == {
        "ACC_PASS_001": "CUST_PASS_001",
        "ACC_PASS_002": "CUST_PASS_002",
    }


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_overlapping_window_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert len(alerts) == 1
    assert alerts[0].evidence_ids == ("TXN_RM_OVERLAP_IN_002", "TXN_RM_OVERLAP_OUT_002")


def test_reordered_input_transactions_produce_same_alert_ids() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()

    first = run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture())
    second = run_rapid_movement_rule(
        frame.sample(frac=1, random_state=5),
        build_rapid_movement_accounts_fixture(),
    )

    assert first[0].alert_id == second[0].alert_id


def test_counterparty_outflow_fixture_triggers_when_enabled() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_counterparty_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_fixture_helpers_are_deterministic() -> None:
    pd.testing.assert_frame_equal(
        build_rapid_movement_trigger_transactions_fixture(),
        build_rapid_movement_trigger_transactions_fixture(),
    )


def test_input_dataframes_are_not_mutated() -> None:
    transactions = build_rapid_movement_trigger_transactions_fixture()
    accounts = build_rapid_movement_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_rapid_movement_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_non_trigger_fixture_produces_no_alert() -> None:
    assert (
        run_rapid_movement_rule(
            build_rapid_movement_non_trigger_transactions_fixture(),
            build_rapid_movement_accounts_fixture(),
        )
        == ()
    )
