"""Tests for end-to-end rapid movement rule execution."""

import pandas as pd
import pytest

from graph_aml.rules import (
    RapidMovementRuleConfig,
    RuleInputError,
    run_rapid_movement_rule,
)
from tests.fixtures.rapid_movement_fixtures import (
    build_rapid_movement_accounts_fixture,
    build_rapid_movement_multi_account_transactions_fixture,
    build_rapid_movement_non_trigger_transactions_fixture,
    build_rapid_movement_trigger_transactions_fixture,
)


def test_run_rapid_movement_rule_returns_no_alerts_for_benign_transactions() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_non_trigger_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert alerts == ()


def test_run_rapid_movement_rule_returns_alerts_for_rapid_movement_activity() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_run_rapid_movement_rule_handles_multiple_accounts() -> None:
    alerts = run_rapid_movement_rule(
        build_rapid_movement_multi_account_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
    )

    assert [alert.account_id for alert in alerts] == ["ACC_PASS_001", "ACC_PASS_002"]


def test_run_rapid_movement_rule_ignores_self_transfers() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "receiver_account_id"] = "ACC_PASS_001"

    alerts = run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture())

    assert alerts == ()


def test_run_rapid_movement_rule_ignores_unsupported_transaction_types() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()
    frame.loc[1, "transaction_type"] = "card"

    alerts = run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture())

    assert alerts == ()


def test_run_rapid_movement_rule_respects_custom_ratio_and_window() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture(sent_amount=8000.0)
    config = RapidMovementRuleConfig(min_outflow_ratio=0.8, max_retained_ratio=0.2)

    alerts = run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture(), config)

    assert len(alerts) == 1


def test_run_rapid_movement_rule_respects_minimum_total_received() -> None:
    config = RapidMovementRuleConfig(min_total_received=11000)

    alerts = run_rapid_movement_rule(
        build_rapid_movement_trigger_transactions_fixture(),
        build_rapid_movement_accounts_fixture(),
        config,
    )

    assert alerts == ()


def test_run_rapid_movement_rule_respects_maximum_retained_ratio() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture(sent_amount=8500)
    config = RapidMovementRuleConfig(min_outflow_ratio=0.8, max_retained_ratio=0.1)

    alerts = run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture(), config)

    assert alerts == ()


def test_run_rapid_movement_rule_returns_deterministic_alert_ids() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture()

    first = run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture())
    second = run_rapid_movement_rule(frame.iloc[::-1], build_rapid_movement_accounts_fixture())

    assert first[0].alert_id == second[0].alert_id


def test_run_rapid_movement_rule_does_not_mutate_inputs() -> None:
    transactions = build_rapid_movement_trigger_transactions_fixture()
    accounts = build_rapid_movement_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_rapid_movement_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_rapid_movement_rule_raises_for_invalid_inputs() -> None:
    frame = build_rapid_movement_trigger_transactions_fixture().drop(columns=["counterparty_id"])

    with pytest.raises(RuleInputError):
        run_rapid_movement_rule(frame, build_rapid_movement_accounts_fixture())
