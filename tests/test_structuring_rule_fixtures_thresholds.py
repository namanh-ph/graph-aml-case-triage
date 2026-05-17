"""Fixture-based threshold boundary tests for structuring candidates."""

import pandas as pd

from graph_aml.rules import (
    StructuringRuleConfig,
    filter_structuring_candidate_transactions,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_boundary_transactions_fixture,
)


def test_amount_equal_to_threshold_times_margin_is_included() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert "TXN_STRUCT_BOUNDARY_002" in set(candidates["transaction_id"])


def test_amount_just_below_margin_is_excluded() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert "TXN_STRUCT_BOUNDARY_001" not in set(candidates["transaction_id"])


def test_amount_just_below_reporting_threshold_is_included() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert "TXN_STRUCT_BOUNDARY_003" in set(candidates["transaction_id"])


def test_amount_equal_to_reporting_threshold_is_excluded() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert "TXN_STRUCT_BOUNDARY_004" not in set(candidates["transaction_id"])


def test_amount_above_reporting_threshold_is_excluded() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert "TXN_STRUCT_BOUNDARY_005" not in set(candidates["transaction_id"])


def test_custom_reporting_threshold_changes_candidate_selection() -> None:
    frame = build_structuring_boundary_transactions_fixture()
    extra = frame.iloc[[0]].copy()
    extra["transaction_id"] = "TXN_STRUCT_BOUNDARY_CUSTOM"
    extra["amount"] = 15000.0
    frame = pd.concat([frame, extra], ignore_index=True)
    config = StructuringRuleConfig(reporting_threshold=20000.0, below_threshold_margin=0.75)

    candidates = filter_structuring_candidate_transactions(frame, config)

    assert "TXN_STRUCT_BOUNDARY_CUSTOM" in set(candidates["transaction_id"])


def test_custom_below_threshold_margin_changes_candidate_selection() -> None:
    config = StructuringRuleConfig(below_threshold_margin=0.89)

    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture(),
        config,
    )

    assert "TXN_STRUCT_BOUNDARY_001" in set(candidates["transaction_id"])


def test_candidate_output_ordering_is_deterministic() -> None:
    frame = build_structuring_boundary_transactions_fixture().sample(frac=1, random_state=7)

    candidates = filter_structuring_candidate_transactions(frame)

    assert candidates["transaction_id"].tolist() == [
        "TXN_STRUCT_BOUNDARY_002",
        "TXN_STRUCT_BOUNDARY_003",
    ]


def test_candidate_output_includes_canonical_account_id() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert candidates["account_id"].eq("ACC_STRUCT_001").all()


def test_candidate_output_preserves_transaction_ids() -> None:
    candidates = filter_structuring_candidate_transactions(
        build_structuring_boundary_transactions_fixture()
    )

    assert candidates["transaction_id"].tolist() == [
        "TXN_STRUCT_BOUNDARY_002",
        "TXN_STRUCT_BOUNDARY_003",
    ]
