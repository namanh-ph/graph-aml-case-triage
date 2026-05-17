"""End-to-end tests for the deterministic fan-out rule."""

import pandas as pd
import pytest

from graph_aml.rules import FanOutRuleConfig, RuleInputError, run_fan_out_rule
from tests.fixtures.fan_out_fixtures import (
    build_fan_out_accounts_fixture,
    build_fan_out_multi_sender_transactions_fixture,
    build_fan_out_non_trigger_transactions_fixture,
    build_fan_out_trigger_transactions_fixture,
)


def test_run_fan_out_rule_returns_no_alerts_for_benign_transactions() -> None:
    assert (
        run_fan_out_rule(
            build_fan_out_non_trigger_transactions_fixture(),
            build_fan_out_accounts_fixture(),
        )
        == ()
    )


def test_run_fan_out_rule_returns_alerts_for_fan_out_like_transactions() -> None:
    alerts = run_fan_out_rule(
        build_fan_out_trigger_transactions_fixture(),
        build_fan_out_accounts_fixture(),
    )

    assert len(alerts) == 1


def test_run_fan_out_rule_handles_multiple_sending_accounts() -> None:
    alerts = run_fan_out_rule(
        build_fan_out_multi_sender_transactions_fixture(),
        build_fan_out_accounts_fixture(),
    )

    assert [alert.account_id for alert in alerts] == ["ACC_DISPERSE_001", "ACC_DISPERSE_002"]


def test_run_fan_out_rule_ignores_self_transfers() -> None:
    frame = build_fan_out_trigger_transactions_fixture(unique_recipient_count=2)
    frame["receiver_account_id"] = "ACC_DISPERSE_001"

    assert run_fan_out_rule(frame, build_fan_out_accounts_fixture()) == ()


def test_run_fan_out_rule_ignores_unsupported_transaction_types() -> None:
    frame = build_fan_out_trigger_transactions_fixture()
    frame["transaction_type"] = "card"

    assert run_fan_out_rule(frame, build_fan_out_accounts_fixture()) == ()


def test_run_fan_out_rule_respects_custom_recipient_threshold_and_window() -> None:
    config = FanOutRuleConfig(min_unique_recipients=4, window_days=2)
    frame = build_fan_out_trigger_transactions_fixture(unique_recipient_count=4)

    assert len(run_fan_out_rule(frame, build_fan_out_accounts_fixture(), config)) == 1


def test_run_fan_out_rule_respects_minimum_total_amount() -> None:
    config = FanOutRuleConfig(min_total_amount=15000)

    assert (
        run_fan_out_rule(
            build_fan_out_trigger_transactions_fixture(),
            build_fan_out_accounts_fixture(),
            config,
        )
        == ()
    )


def test_run_fan_out_rule_returns_deterministic_alert_ids() -> None:
    first = run_fan_out_rule(
        build_fan_out_trigger_transactions_fixture(),
        build_fan_out_accounts_fixture(),
    )
    second = run_fan_out_rule(
        build_fan_out_trigger_transactions_fixture(),
        build_fan_out_accounts_fixture(),
    )

    assert first[0].alert_id == second[0].alert_id


def test_run_fan_out_rule_does_not_mutate_input_dataframes() -> None:
    transactions = build_fan_out_trigger_transactions_fixture()
    accounts = build_fan_out_accounts_fixture()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)

    run_fan_out_rule(transactions, accounts)

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_run_fan_out_rule_raises_for_invalid_inputs() -> None:
    with pytest.raises(RuleInputError):
        run_fan_out_rule(
            pd.DataFrame({"transaction_id": ["TXN"]}),
            build_fan_out_accounts_fixture(),
        )
