"""Focused fixture tests for dormant reactivation rule behaviour."""

import pandas as pd

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    detect_dormant_reactivation_windows,
    run_dormant_reactivation_rule,
)
from tests.fixtures.dormant_reactivation_fixtures import (
    build_dormant_reactivation_accounts_fixture,
    build_dormant_reactivation_counterparty_transactions_fixture,
    build_dormant_reactivation_multi_account_transactions_fixture,
    build_dormant_reactivation_overlapping_window_transactions_fixture,
    build_dormant_reactivation_trigger_transactions_fixture,
)


def test_exact_trigger_fixture_produces_one_alert() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_trigger_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_dormant_period_followed_by_sufficient_outbound_activity_triggers() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_trigger_transactions_fixture(outbound_amount=15000.0),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert alerts[0].account_id == "ACC_DORMANT_001"


def test_dormant_period_below_threshold_produces_no_alert() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture(
        prior_timestamp="2025-01-01 09:00:00"
    )

    assert (
        run_dormant_reactivation_rule(
            frame,
            build_dormant_reactivation_accounts_fixture(),
        )
        == ()
    )


def test_outbound_activity_below_value_threshold_produces_no_alert() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture(outbound_amount=9000.0)

    assert (
        run_dormant_reactivation_rule(
            frame,
            build_dormant_reactivation_accounts_fixture(),
        )
        == ()
    )


def test_reactivation_activity_outside_window_is_excluded() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    second = frame.iloc[1].copy()
    second["transaction_id"] = "TXN_DR_REACT_LATE"
    second["transaction_timestamp"] = pd.Timestamp("2025-01-20 09:00:00", tz="UTC")
    second["amount"] = 5000.0
    frame = pd.DataFrame([*frame.to_dict("records"), second.to_dict()])

    output = detect_dormant_reactivation_windows(frame)

    assert output.loc[0, "reactivation_evidence_ids"] == ("TXN_DR_REACT_001",)


def test_account_with_no_prior_activity_produces_no_alert() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture().iloc[[1]]

    assert (
        run_dormant_reactivation_rule(
            frame,
            build_dormant_reactivation_accounts_fixture(),
        )
        == ()
    )


def test_multiple_dormant_accounts_produce_distinct_alerts() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_multi_account_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert {alert.account_id for alert in alerts} == {"ACC_DORMANT_001", "ACC_DORMANT_002"}


def test_evidence_ids_do_not_leak_across_accounts() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_multi_account_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    first = next(alert for alert in alerts if alert.account_id == "ACC_DORMANT_001")
    assert "TXN_DR_MULTI_B_REACT" not in first.evidence_ids


def test_customer_ids_are_attached_correctly_for_dormant_accounts() -> None:
    alert = run_dormant_reactivation_rule(
        build_dormant_reactivation_trigger_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )[0]

    assert alert.customer_id == "CUST_DORMANT_001"


def test_overlapping_reactivation_windows_are_deduplicated_deterministically() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_overlapping_window_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert len(alerts) == 1
    assert alerts[0].evidence_ids == (
        "TXN_DR_OVERLAP_PRIOR",
        "TXN_DR_OVERLAP_REACT_001",
        "TXN_DR_OVERLAP_REACT_002",
    )


def test_reordered_input_transactions_produce_same_alert_ids() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()

    first = run_dormant_reactivation_rule(
        frame,
        build_dormant_reactivation_accounts_fixture(),
    )
    second = run_dormant_reactivation_rule(
        frame.sample(frac=1, random_state=2),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert first[0].alert_id == second[0].alert_id


def test_counterparty_outflow_fixtures_trigger_when_enabled() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_counterparty_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_fixture_helpers_produce_deterministic_dataframes() -> None:
    first = build_dormant_reactivation_trigger_transactions_fixture()
    second = build_dormant_reactivation_trigger_transactions_fixture()

    pd.testing.assert_frame_equal(first, second)


def test_input_dataframes_are_not_mutated() -> None:
    transactions = build_dormant_reactivation_trigger_transactions_fixture()
    accounts = build_dormant_reactivation_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_dormant_reactivation_rule(
        transactions,
        accounts,
        DormantReactivationRuleConfig(),
    )

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)
