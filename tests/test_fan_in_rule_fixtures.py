"""Focused fixture tests for fan-in rule behavior."""

import pandas as pd

from graph_aml.rules import (
    detect_fan_in_windows,
    run_fan_in_rule,
    summarise_rule_alerts,
)
from tests.fixtures.fan_in_fixtures import (
    build_fan_in_accounts_fixture,
    build_fan_in_multi_receiver_transactions_fixture,
    build_fan_in_overlapping_window_transactions_fixture,
    build_fan_in_trigger_transactions_fixture,
)


def test_exact_trigger_fixture_produces_one_alert() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_trigger_transactions_fixture(),
        build_fan_in_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_one_fewer_than_sender_threshold_produces_no_alert() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_trigger_transactions_fixture(unique_sender_count=14),
        build_fan_in_accounts_fixture(),
    )

    assert alerts == ()


def test_repeated_transfers_from_same_sender_do_not_inflate_unique_sender_count() -> None:
    frame = build_fan_in_trigger_transactions_fixture(unique_sender_count=15)
    frame["sender_account_id"] = "ACC_FAN_SENDER_001"

    assert run_fan_in_rule(frame, build_fan_in_accounts_fixture()) == ()


def test_multiple_receiver_accounts_produce_distinct_alerts() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_multi_receiver_transactions_fixture(),
        build_fan_in_accounts_fixture(),
    )

    assert len(alerts) == 2
    assert alerts[0].alert_id != alerts[1].alert_id


def test_evidence_ids_do_not_leak_across_receiver_accounts() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_multi_receiver_transactions_fixture(),
        build_fan_in_accounts_fixture(),
    )

    for alert in alerts:
        marker = "_A_" if alert.account_id == "ACC_COLLECT_001" else "_B_"
        assert all(marker in evidence_id for evidence_id in alert.evidence_ids)


def test_customer_ids_are_attached_for_receiving_accounts() -> None:
    alerts = run_fan_in_rule(
        build_fan_in_multi_receiver_transactions_fixture(),
        build_fan_in_accounts_fixture(),
    )

    assert {alert.account_id: alert.customer_id for alert in alerts} == {
        "ACC_COLLECT_001": "CUST_COLLECT_001",
        "ACC_COLLECT_002": "CUST_COLLECT_002",
    }


def test_overlapping_windows_are_deduplicated_deterministically() -> None:
    output = detect_fan_in_windows(build_fan_in_overlapping_window_transactions_fixture())

    assert len(output) == 1
    assert output.loc[0, "unique_sender_count"] == 16


def test_reordered_input_transactions_produce_same_alert_ids() -> None:
    accounts = build_fan_in_accounts_fixture()
    transactions = build_fan_in_trigger_transactions_fixture()

    first = run_fan_in_rule(transactions, accounts)
    second = run_fan_in_rule(transactions.sample(frac=1, random_state=3), accounts)

    assert first[0].alert_id == second[0].alert_id


def test_fixture_helpers_produce_deterministic_dataframes() -> None:
    first = build_fan_in_trigger_transactions_fixture()
    second = build_fan_in_trigger_transactions_fixture()

    pd.testing.assert_frame_equal(first, second)


def test_input_dataframes_are_not_mutated() -> None:
    transactions = build_fan_in_trigger_transactions_fixture()
    accounts = build_fan_in_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_fan_in_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_fixture_detection_summary_counts_match_receivers() -> None:
    summary = summarise_rule_alerts(
        run_fan_in_rule(
            build_fan_in_multi_receiver_transactions_fixture(),
            build_fan_in_accounts_fixture(),
        )
    )

    assert summary["alert_count"] == 2
