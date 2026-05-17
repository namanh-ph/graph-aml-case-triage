"""Deterministic alert ID regression tests for fan-flow rules."""

import pandas as pd

from graph_aml.rules import FanInRuleConfig, FanOutRuleConfig, run_fan_in_rule, run_fan_out_rule
from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
    build_joint_fan_in_and_fan_out_transactions_fixture,
)


def _fan_in_config() -> FanInRuleConfig:
    return FanInRuleConfig(min_unique_senders=4)


def _fan_out_config() -> FanOutRuleConfig:
    return FanOutRuleConfig(min_unique_recipients=4)


def test_running_fan_in_same_fixture_twice_produces_identical_alert_ids() -> None:
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_in_rule(build_fan_in_only_transactions_fixture(), accounts, _fan_in_config())
    second = run_fan_in_rule(build_fan_in_only_transactions_fixture(), accounts, _fan_in_config())

    assert first[0].alert_id == second[0].alert_id


def test_running_fan_out_same_fixture_twice_produces_identical_alert_ids() -> None:
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_out_rule(build_fan_out_only_transactions_fixture(), accounts, _fan_out_config())
    second = run_fan_out_rule(
        build_fan_out_only_transactions_fixture(), accounts, _fan_out_config()
    )

    assert first[0].alert_id == second[0].alert_id


def test_reordering_fan_in_transactions_does_not_change_alert_ids() -> None:
    frame = build_fan_in_only_transactions_fixture()
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_in_rule(frame, accounts, _fan_in_config())
    second = run_fan_in_rule(frame.sample(frac=1, random_state=7), accounts, _fan_in_config())

    assert first[0].alert_id == second[0].alert_id


def test_reordering_fan_out_transactions_does_not_change_alert_ids() -> None:
    frame = build_fan_out_only_transactions_fixture()
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_out_rule(frame, accounts, _fan_out_config())
    second = run_fan_out_rule(frame.sample(frac=1, random_state=7), accounts, _fan_out_config())

    assert first[0].alert_id == second[0].alert_id


def test_changing_fan_in_receiving_account_changes_alert_id() -> None:
    frame = build_fan_in_only_transactions_fixture()
    changed = frame.copy()
    changed["receiver_account_id"] = "ACC_COLLECT_002"
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_in_rule(frame, accounts, _fan_in_config())
    second = run_fan_in_rule(changed, accounts, _fan_in_config())

    assert first[0].alert_id != second[0].alert_id


def test_changing_fan_out_sending_account_changes_alert_id() -> None:
    frame = build_fan_out_only_transactions_fixture()
    changed = frame.copy()
    changed["sender_account_id"] = "ACC_DISPERSE_002"
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_out_rule(frame, accounts, _fan_out_config())
    second = run_fan_out_rule(changed, accounts, _fan_out_config())

    assert first[0].alert_id != second[0].alert_id


def test_changing_fan_in_detection_window_changes_alert_id() -> None:
    frame = build_fan_in_only_transactions_fixture()
    changed = build_fan_in_only_transactions_fixture()
    changed["transaction_timestamp"] = changed["transaction_timestamp"] + pd.Timedelta(days=1)
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_in_rule(frame, accounts, _fan_in_config())
    second = run_fan_in_rule(changed, accounts, _fan_in_config())

    assert first[0].alert_id != second[0].alert_id


def test_changing_fan_out_detection_window_changes_alert_id() -> None:
    frame = build_fan_out_only_transactions_fixture()
    changed = build_fan_out_only_transactions_fixture()
    changed["transaction_timestamp"] = changed["transaction_timestamp"] + pd.Timedelta(days=1)
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_out_rule(frame, accounts, _fan_out_config())
    second = run_fan_out_rule(changed, accounts, _fan_out_config())

    assert first[0].alert_id != second[0].alert_id


def test_changing_fan_in_evidence_transactions_changes_alert_id() -> None:
    frame = build_fan_in_only_transactions_fixture()
    changed = frame.copy()
    changed.loc[0, "transaction_id"] = "TXN_FLOW_IN_CHANGED_001"
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_in_rule(frame, accounts, _fan_in_config())
    second = run_fan_in_rule(changed, accounts, _fan_in_config())

    assert first[0].alert_id != second[0].alert_id


def test_changing_fan_out_evidence_transactions_changes_alert_id() -> None:
    frame = build_fan_out_only_transactions_fixture()
    changed = frame.copy()
    changed.loc[0, "transaction_id"] = "TXN_FLOW_OUT_CHANGED_001"
    accounts = build_fan_flow_accounts_fixture()

    first = run_fan_out_rule(frame, accounts, _fan_out_config())
    second = run_fan_out_rule(changed, accounts, _fan_out_config())

    assert first[0].alert_id != second[0].alert_id


def test_fan_in_and_fan_out_alert_ids_do_not_collide_on_same_fixture() -> None:
    frame = build_joint_fan_in_and_fan_out_transactions_fixture()
    accounts = build_fan_flow_accounts_fixture()

    fan_in_id = run_fan_in_rule(frame, accounts, _fan_in_config())[0].alert_id
    fan_out_id = run_fan_out_rule(frame, accounts, _fan_out_config())[0].alert_id

    assert fan_in_id != fan_out_id
