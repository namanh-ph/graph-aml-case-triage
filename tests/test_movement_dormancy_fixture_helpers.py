"""Index tests for joint movement-dormancy fixture helpers."""

import importlib

import pandas as pd

from tests.fixtures import movement_dormancy_fixtures as fixtures

REQUIRED_ACCOUNT_COLUMNS = {"account_id", "customer_id"}
REQUIRED_TRANSACTION_COLUMNS = {
    "transaction_id",
    "sender_account_id",
    "receiver_account_id",
    "counterparty_id",
    "transaction_timestamp",
    "amount",
    "transaction_type",
}


def test_movement_dormancy_fixture_module_imports() -> None:
    assert importlib.import_module("tests.fixtures.movement_dormancy_fixtures")


def test_account_fixture_contains_required_account_columns() -> None:
    accounts = fixtures.build_movement_dormancy_accounts_fixture()

    assert REQUIRED_ACCOUNT_COLUMNS.issubset(accounts.columns)
    assert {
        "ACC_PASS_001",
        "ACC_DORMANT_001",
        "ACC_MD_SOURCE_001",
        "ACC_MD_RECIPIENT_001",
        "ACC_MD_COUNTERPARTY_ONLY",
        "ACC_BENIGN_001",
    }.issubset(set(accounts["account_id"]))


def test_transaction_fixtures_contain_required_transaction_columns() -> None:
    for builder in _transaction_builders():
        assert REQUIRED_TRANSACTION_COLUMNS.issubset(builder().columns), builder.__name__


def test_joint_fixture_contains_both_rule_patterns() -> None:
    frame = fixtures.build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()

    assert frame["typology_label"].eq("rapid_movement").any()
    assert frame["typology_label"].eq("dormant_reactivation").any()


def test_rapid_movement_only_fixture_contains_pass_through_pattern() -> None:
    frame = fixtures.build_rapid_movement_only_transactions_fixture()

    assert "ACC_PASS_001" in set(frame["receiver_account_id"])
    assert "ACC_PASS_001" in set(frame["sender_account_id"])


def test_dormant_only_fixture_contains_prior_and_reactivation_pattern() -> None:
    frame = fixtures.build_dormant_reactivation_only_transactions_fixture()

    assert frame["transaction_id"].str.contains("PRIOR").any()
    assert frame["transaction_id"].str.contains("REACT").any()


def test_boundary_fixture_contains_window_and_just_outside_examples() -> None:
    frame = fixtures.build_movement_dormancy_window_boundary_transactions_fixture()

    assert "TXN_MD_BOUNDARY_RM_OUT_END" in set(frame["transaction_id"])
    assert "TXN_MD_BOUNDARY_RM_OUT_LATE" in set(frame["transaction_id"])
    assert "TXN_MD_BOUNDARY_DR_REACT_002" in set(frame["transaction_id"])
    assert "TXN_MD_BOUNDARY_DR_LATE_REACT_002" in set(frame["transaction_id"])


def test_overlapping_fixture_contains_overlapping_candidate_windows() -> None:
    frame = fixtures.build_movement_dormancy_overlapping_window_transactions_fixture()

    assert frame["transaction_id"].str.contains("OVERLAP_RM").sum() >= 4
    assert frame["transaction_id"].str.contains("OVERLAP_DR").sum() >= 3


def test_counterparty_mixed_fixture_includes_internal_and_external_outflows() -> None:
    frame = fixtures.build_movement_dormancy_counterparty_mixed_transactions_fixture()

    assert frame["receiver_account_id"].notna().any()
    assert frame["counterparty_id"].notna().any()


def test_fixture_helpers_are_deterministic() -> None:
    for builder in (fixtures.build_movement_dormancy_accounts_fixture, *_transaction_builders()):
        pd.testing.assert_frame_equal(builder(), builder())


def _transaction_builders():
    return (
        fixtures.build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
        fixtures.build_rapid_movement_only_transactions_fixture,
        fixtures.build_dormant_reactivation_only_transactions_fixture,
        fixtures.build_cross_rule_benign_transactions_fixture,
        fixtures.build_movement_dormancy_window_boundary_transactions_fixture,
        fixtures.build_movement_dormancy_overlapping_window_transactions_fixture,
        fixtures.build_movement_dormancy_counterparty_mixed_transactions_fixture,
        fixtures.build_movement_dormancy_high_value_transactions_fixture,
        fixtures.build_movement_dormancy_invalid_transactions_fixture,
    )
