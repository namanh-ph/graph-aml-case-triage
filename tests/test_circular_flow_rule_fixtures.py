"""Focused fixture tests for circular flow detection."""

import pandas as pd

from graph_aml.rules import CircularFlowDetectionConfig, detect_circular_flows
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_counterparty_transactions_fixture,
    build_circular_flow_four_hop_transactions_fixture,
    build_circular_flow_multi_cycle_transactions_fixture,
    build_circular_flow_non_trigger_transactions_fixture,
    build_circular_flow_overlong_cycle_transactions_fixture,
    build_circular_flow_three_hop_transactions_fixture,
    build_circular_flow_time_span_boundary_transactions_fixture,
    build_circular_flow_two_hop_transactions_fixture,
)


def test_two_hop_fixture_produces_one_detection() -> None:
    detections = detect_circular_flows(build_circular_flow_two_hop_transactions_fixture())

    assert len(detections) == 1


def test_three_hop_fixture_produces_one_detection() -> None:
    detections = detect_circular_flows(build_circular_flow_three_hop_transactions_fixture())

    assert len(detections) == 1
    assert detections.loc[0, "cycle_length"] == 3


def test_four_hop_fixture_produces_one_detection_when_allowed() -> None:
    detections = detect_circular_flows(
        build_circular_flow_four_hop_transactions_fixture(),
        CircularFlowDetectionConfig(max_cycle_hops=4),
    )

    assert len(detections) == 1


def test_overlong_cycle_fixture_produces_no_detection_when_above_hop_limit() -> None:
    detections = detect_circular_flows(build_circular_flow_overlong_cycle_transactions_fixture())

    assert detections.empty


def test_non_trigger_fixture_produces_no_detection() -> None:
    detections = detect_circular_flows(build_circular_flow_non_trigger_transactions_fixture())

    assert detections.empty


def test_time_span_boundary_triggers_exactly_at_configured_max_time_span() -> None:
    detections = detect_circular_flows(
        build_circular_flow_time_span_boundary_transactions_fixture(),
        CircularFlowDetectionConfig(max_time_span_hours=168),
    )

    assert ("ACC_CF_A", "ACC_CF_B") in set(detections["cycle_accounts"])


def test_time_span_boundary_excludes_just_beyond_configured_max_time_span() -> None:
    detections = detect_circular_flows(
        build_circular_flow_time_span_boundary_transactions_fixture(),
        CircularFlowDetectionConfig(max_time_span_hours=167),
    )

    assert detections.empty


def test_multi_cycle_fixture_produces_deterministic_cycle_ordering() -> None:
    transactions = build_circular_flow_multi_cycle_transactions_fixture()

    first = detect_circular_flows(transactions)
    second = detect_circular_flows(transactions)

    assert first["cycle_id"].tolist() == second["cycle_id"].tolist()


def test_counterparty_fixture_contributes_only_when_counterparty_edges_are_enabled() -> None:
    transactions = build_circular_flow_counterparty_transactions_fixture()

    excluded = detect_circular_flows(transactions)
    included = detect_circular_flows(
        transactions,
        CircularFlowDetectionConfig(include_counterparty_edges=True),
    )

    assert excluded.empty
    assert len(included) == 1


def test_fixture_helpers_produce_deterministic_dataframes() -> None:
    first = build_circular_flow_two_hop_transactions_fixture()
    second = build_circular_flow_two_hop_transactions_fixture()

    pd.testing.assert_frame_equal(first, second)


def test_fixture_detection_does_not_mutate_input_dataframes() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()
    original = transactions.copy(deep=True)

    detect_circular_flows(transactions)

    pd.testing.assert_frame_equal(transactions, original)
