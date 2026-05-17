"""Tests for circular flow detection."""

import pandas as pd

from graph_aml.rules import (
    CIRCULAR_FLOW_DETECTION_COLUMNS,
    CircularFlowDetectionConfig,
    detect_circular_flows,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_four_hop_transactions_fixture,
    build_circular_flow_multi_cycle_transactions_fixture,
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_overlong_cycle_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
    build_circular_flow_time_span_boundary_transactions_fixture,
    build_circular_flow_two_hop_transactions_fixture,
)


def test_detection_returns_empty_dataframe_when_no_cycles_exist() -> None:
    detections = detect_circular_flows(build_circular_flow_non_trigger_transactions_fixture())

    assert detections.empty
    assert tuple(detections.columns) == CIRCULAR_FLOW_DETECTION_COLUMNS


def test_detection_identifies_simple_two_hop_cycle() -> None:
    detections = detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())

    assert len(detections) == 1
    assert detections.loc[0, "cycle_length"] == 2


def test_detection_identifies_three_hop_cycle() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    assert len(detections) == 1
    assert detections.loc[0, "cycle_accounts"] == ("ACC_CF_A", "ACC_CF_B", "ACC_CF_C")


def test_detection_identifies_four_hop_cycle_when_allowed() -> None:
    detections = detect_circular_flows(
        build_circular_flow_four_hop_transactions_fixture(),
        CircularFlowDetectionConfig(max_cycle_hops=4),
    )

    assert len(detections) == 1
    assert detections.loc[0, "cycle_length"] == 4


def test_detection_excludes_cycles_longer_than_max_cycle_hops() -> None:
    detections = detect_circular_flows(
        build_circular_flow_overlong_cycle_transactions_fixture(),
        CircularFlowDetectionConfig(max_cycle_hops=4),
    )

    assert detections.empty


def test_detection_excludes_cycles_shorter_than_min_cycle_hops() -> None:
    detections = detect_circular_flows(
        build_circular_flow_two_hop_transactions_fixture(),
        CircularFlowDetectionConfig(min_cycle_hops=3),
    )

    assert detections.empty


def test_detection_respects_minimum_total_amount() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()

    detections = detect_circular_flows(
        transactions,
        CircularFlowDetectionConfig(min_total_amount=10001.0),
    )

    assert detections.empty


def test_detection_respects_max_time_span_hours() -> None:
    detections = detect_circular_flows(
        build_circular_flow_time_span_boundary_transactions_fixture(),
        CircularFlowDetectionConfig(max_time_span_hours=168),
    )

    assert len(detections) == 1
    assert detections.loc[0, "cycle_accounts"] == ("ACC_CF_A", "ACC_CF_B")


def test_detection_produces_deterministic_cycle_ids() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()

    first = detect_circular_flows(transactions)
    second = detect_circular_flows(transactions)

    assert first["cycle_id"].tolist() == second["cycle_id"].tolist()


def test_detection_deduplicates_equivalent_rotated_cycles() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()

    detections = detect_circular_flows(transactions)

    assert len(detections) == 1


def test_detection_limits_cycles_per_primary_account() -> None:
    detections = detect_circular_flows(
        build_circular_flow_multi_cycle_transactions_fixture(),
        CircularFlowDetectionConfig(max_cycles_per_account=2),
    )

    assert len(detections.loc[detections["primary_account_id"].eq("ACC_CF_A")]) == 2


def test_detection_limits_total_cycles() -> None:
    detections = detect_circular_flows(
        build_circular_flow_multi_cycle_transactions_fixture(),
        CircularFlowDetectionConfig(max_total_cycles=2),
    )

    assert len(detections) == 2


def test_detection_output_columns_equal_expected_columns() -> None:
    detections = detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())

    assert tuple(detections.columns) == CIRCULAR_FLOW_DETECTION_COLUMNS


def test_detection_evidence_ids_are_deterministic_and_non_empty() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    assert detections.loc[0, "evidence_ids"] == (
        "TXN_CF_3HOP_001",
        "TXN_CF_3HOP_002",
        "TXN_CF_3HOP_003",
    )


def test_detection_output_ordering_is_deterministic() -> None:
    transactions = build_circular_flow_multi_cycle_transactions_fixture()

    detections = detect_circular_flows(transactions)

    assert detections["cycle_id"].tolist() == sorted(
        detections["cycle_id"].tolist(),
        key=lambda cycle_id: (
            detections.loc[detections["cycle_id"].eq(cycle_id), "primary_account_id"].iloc[0],
            detections.loc[detections["cycle_id"].eq(cycle_id), "cycle_length"].iloc[0],
            detections.loc[
                detections["cycle_id"].eq(cycle_id),
                "detection_window_start",
            ].iloc[0],
            cycle_id,
        ),
    )


def test_detection_does_not_mutate_inputs() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()
    original = transactions.copy(deep=True)

    detect_circular_flows(transactions)

    pd.testing.assert_frame_equal(transactions, original)
