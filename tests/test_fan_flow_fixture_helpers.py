"""Index tests for joint fan-flow fixture helpers."""

import importlib

import pandas as pd

from tests.fixtures import fan_flow_fixtures
from tests.fixtures.fan_flow_fixtures import (
    TRANSACTION_COLUMNS,
    build_cross_rule_non_trigger_transactions_fixture,
    build_fan_flow_accounts_fixture,
    build_fan_flow_boundary_transactions_fixture,
    build_fan_flow_counterparty_mixed_transactions_fixture,
    build_fan_flow_duplicate_sender_recipient_fixture,
    build_fan_flow_invalid_transactions_fixture,
    build_fan_flow_overlapping_window_transactions_fixture,
    build_fan_in_only_transactions_fixture,
    build_fan_out_only_transactions_fixture,
    build_joint_fan_in_and_fan_out_transactions_fixture,
)


def test_fan_flow_fixture_module_imports_successfully() -> None:
    assert importlib.import_module("tests.fixtures.fan_flow_fixtures") is fan_flow_fixtures


def test_account_fixture_contains_required_account_columns() -> None:
    accounts = build_fan_flow_accounts_fixture()

    assert {"account_id", "customer_id"}.issubset(accounts.columns)


def test_transaction_fixtures_contain_required_transaction_columns() -> None:
    builders = (
        build_joint_fan_in_and_fan_out_transactions_fixture,
        build_fan_in_only_transactions_fixture,
        build_fan_out_only_transactions_fixture,
        build_cross_rule_non_trigger_transactions_fixture,
        build_fan_flow_boundary_transactions_fixture,
        build_fan_flow_overlapping_window_transactions_fixture,
        build_fan_flow_counterparty_mixed_transactions_fixture,
        build_fan_flow_duplicate_sender_recipient_fixture,
        build_fan_flow_invalid_transactions_fixture,
    )

    for builder in builders:
        assert set(TRANSACTION_COLUMNS).issubset(builder().columns)


def test_joint_fixture_contains_fan_in_and_fan_out_activity() -> None:
    frame = build_joint_fan_in_and_fan_out_transactions_fixture()

    assert {"fan_in", "fan_out"}.issubset(set(frame["typology_label"].dropna()))


def test_fan_in_only_fixture_contains_receiving_account_concentration() -> None:
    frame = build_fan_in_only_transactions_fixture()

    assert frame["receiver_account_id"].nunique() == 1
    assert frame["sender_account_id"].nunique() == 4


def test_fan_out_only_fixture_contains_sending_account_dispersion() -> None:
    frame = build_fan_out_only_transactions_fixture()

    assert frame["sender_account_id"].nunique() == 1
    assert frame["receiver_account_id"].nunique() == 4


def test_boundary_fixture_contains_exact_and_below_threshold_examples() -> None:
    frame = build_fan_flow_boundary_transactions_fixture()

    assert frame["transaction_id"].str.contains("EXACT").any()
    assert frame["transaction_id"].str.contains("BELOW").any()


def test_overlapping_window_fixture_contains_overlapping_candidates_for_both_rules() -> None:
    frame = build_fan_flow_overlapping_window_transactions_fixture()

    assert frame["transaction_id"].str.contains("OVERLAP_IN").any()
    assert frame["transaction_id"].str.contains("OVERLAP_OUT").any()


def test_counterparty_mixed_fixture_includes_internal_and_external_recipient_patterns() -> None:
    frame = build_fan_flow_counterparty_mixed_transactions_fixture()

    assert frame["receiver_account_id"].notna().any()
    assert frame["counterparty_id"].notna().any()


def test_fixture_helpers_produce_deterministic_dataframes_across_calls() -> None:
    first = build_joint_fan_in_and_fan_out_transactions_fixture()
    second = build_joint_fan_in_and_fan_out_transactions_fixture()

    pd.testing.assert_frame_equal(first, second)
