"""Tests for circular flow transaction evidence selection."""

import pandas as pd
import pytest

from graph_aml.rules import (
    CIRCULAR_FLOW_EDGE_COLUMNS,
    RuleExecutionError,
    build_circular_flow_edges,
    select_cycle_edge_evidence,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_three_hop_transactions_fixture,
)


def test_evidence_selection_returns_rows_for_each_cycle_edge() -> None:
    edges = build_circular_flow_edges(build_circular_flow_three_hop_transactions_fixture())

    evidence = select_cycle_edge_evidence(("ACC_CF_A", "ACC_CF_B", "ACC_CF_C"), edges)

    assert len(evidence) == 3
    assert set(evidence["transaction_id"]) == {
        "TXN_CF_3HOP_001",
        "TXN_CF_3HOP_002",
        "TXN_CF_3HOP_003",
    }


def test_evidence_selection_includes_multiple_transactions_on_same_directed_edge() -> None:
    transactions = build_circular_flow_three_hop_transactions_fixture()
    duplicate = transactions.iloc[[0]].copy()
    duplicate.loc[:, "transaction_id"] = "TXN_CF_3HOP_001_DUP"
    duplicate.loc[:, "transaction_timestamp"] = "2025-01-10 09:30:00"
    edges = build_circular_flow_edges(pd.concat([transactions, duplicate], ignore_index=True))

    evidence = select_cycle_edge_evidence(("ACC_CF_A", "ACC_CF_B", "ACC_CF_C"), edges)

    assert "TXN_CF_3HOP_001_DUP" in set(evidence["transaction_id"])
    assert len(evidence) == 4


def test_evidence_selection_orders_by_cycle_step_then_timestamp_then_transaction_id() -> None:
    edges = build_circular_flow_edges(build_circular_flow_three_hop_transactions_fixture())

    evidence = select_cycle_edge_evidence(("ACC_CF_B", "ACC_CF_C", "ACC_CF_A"), edges)

    assert evidence["transaction_id"].tolist() == [
        "TXN_CF_3HOP_001",
        "TXN_CF_3HOP_002",
        "TXN_CF_3HOP_003",
    ]


def test_missing_evidence_for_cycle_step_raises() -> None:
    edges = build_circular_flow_edges(build_circular_flow_three_hop_transactions_fixture())
    edges = edges.loc[edges["transaction_id"].ne("TXN_CF_3HOP_002")].copy()

    with pytest.raises(RuleExecutionError):
        select_cycle_edge_evidence(("ACC_CF_A", "ACC_CF_B", "ACC_CF_C"), edges)


def test_evidence_output_columns_equal_expected_columns() -> None:
    edges = build_circular_flow_edges(build_circular_flow_three_hop_transactions_fixture())

    evidence = select_cycle_edge_evidence(("ACC_CF_A", "ACC_CF_B", "ACC_CF_C"), edges)

    assert tuple(evidence.columns) == CIRCULAR_FLOW_EDGE_COLUMNS


def test_evidence_selection_does_not_mutate_edges() -> None:
    edges = build_circular_flow_edges(build_circular_flow_three_hop_transactions_fixture())
    original = edges.copy(deep=True)

    select_cycle_edge_evidence(("ACC_CF_A", "ACC_CF_B", "ACC_CF_C"), edges)

    pd.testing.assert_frame_equal(edges, original)
