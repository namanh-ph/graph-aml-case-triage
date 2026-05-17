"""Tests for end-to-end dormant reactivation rule execution."""

import pandas as pd
import pytest

from graph_aml.rules import (
    DormantReactivationRuleConfig,
    RuleInputError,
    run_dormant_reactivation_rule,
)
from tests.fixtures.dormant_reactivation_fixtures import (
    build_dormant_reactivation_accounts_fixture,
    build_dormant_reactivation_multi_account_transactions_fixture,
    build_dormant_reactivation_non_trigger_transactions_fixture,
    build_dormant_reactivation_trigger_transactions_fixture,
)


def test_run_dormant_reactivation_rule_returns_no_alerts_for_benign_transactions() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_non_trigger_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert alerts == ()


def test_run_dormant_reactivation_rule_returns_alerts_for_dormant_activity() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_trigger_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_run_dormant_reactivation_rule_handles_multiple_accounts() -> None:
    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_multi_account_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
    )

    assert [alert.account_id for alert in alerts] == [
        "ACC_DORMANT_001",
        "ACC_DORMANT_002",
    ]


def test_run_dormant_reactivation_rule_ignores_self_transfers() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    frame.loc[1, "receiver_account_id"] = "ACC_DORMANT_001"

    alerts = run_dormant_reactivation_rule(
        frame,
        build_dormant_reactivation_accounts_fixture(),
    )

    assert alerts == ()


def test_run_dormant_reactivation_rule_ignores_unsupported_transaction_types() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()
    frame.loc[1, "transaction_type"] = "card"

    alerts = run_dormant_reactivation_rule(
        frame,
        build_dormant_reactivation_accounts_fixture(),
    )

    assert alerts == ()


def test_run_dormant_reactivation_rule_respects_custom_dormancy_and_window() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture(
        prior_timestamp="2024-12-20 09:00:00"
    )
    config = DormantReactivationRuleConfig(dormant_days_threshold=20)

    alerts = run_dormant_reactivation_rule(
        frame,
        build_dormant_reactivation_accounts_fixture(),
        config,
    )

    assert len(alerts) == 1


def test_run_dormant_reactivation_rule_respects_minimum_total_outbound_amount() -> None:
    config = DormantReactivationRuleConfig(min_total_outbound_amount=11000)

    alerts = run_dormant_reactivation_rule(
        build_dormant_reactivation_trigger_transactions_fixture(),
        build_dormant_reactivation_accounts_fixture(),
        config,
    )

    assert alerts == ()


def test_run_dormant_reactivation_rule_returns_deterministic_alert_ids() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture()

    first = run_dormant_reactivation_rule(
        frame,
        build_dormant_reactivation_accounts_fixture(),
    )
    second = run_dormant_reactivation_rule(
        frame.iloc[::-1],
        build_dormant_reactivation_accounts_fixture(),
    )

    assert first[0].alert_id == second[0].alert_id


def test_run_dormant_reactivation_rule_does_not_mutate_inputs() -> None:
    transactions = build_dormant_reactivation_trigger_transactions_fixture()
    accounts = build_dormant_reactivation_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_dormant_reactivation_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_dormant_reactivation_rule_raises_for_invalid_inputs() -> None:
    frame = build_dormant_reactivation_trigger_transactions_fixture().drop(
        columns=["counterparty_id"]
    )

    with pytest.raises(RuleInputError):
        run_dormant_reactivation_rule(
            frame,
            build_dormant_reactivation_accounts_fixture(),
        )
