"""Tests for circular flow transaction preparation and edge construction."""

import pandas as pd

from graph_aml.rules import (
    CIRCULAR_FLOW_EDGE_COLUMNS,
    CircularFlowDetectionConfig,
    build_circular_flow_edges,
    prepare_circular_flow_transactions,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_counterparty_transactions_fixture,
    build_circular_flow_two_hop_transactions_fixture,
)


def test_preparation_parses_timestamps_and_coerces_amounts() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()
    transactions.loc[0, "transaction_timestamp"] = "2025-01-10 09:00:00"
    transactions["amount"] = transactions["amount"].astype(object)
    transactions.loc[0, "amount"] = "5000.50"

    prepared = prepare_circular_flow_transactions(transactions)

    assert pd.api.types.is_datetime64_any_dtype(prepared["transaction_timestamp"])
    assert float(prepared.loc[0, "amount"]) == 5000.5


def test_preparation_lowercases_and_filters_transaction_types() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()
    transactions.loc[0, "transaction_type"] = "WIRE"
    transactions.loc[1, "transaction_type"] = "cash_deposit"

    prepared = prepare_circular_flow_transactions(transactions)

    assert prepared["transaction_type"].tolist() == ["wire"]


def test_preparation_excludes_and_keeps_self_loops_by_config() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()
    self_loop = transactions.iloc[[0]].copy()
    self_loop.loc[:, "transaction_id"] = "TXN_CF_SELF_LOOP"
    self_loop.loc[:, "sender_account_id"] = "ACC_CF_A"
    self_loop.loc[:, "receiver_account_id"] = "ACC_CF_A"
    transactions = pd.concat([transactions, self_loop], ignore_index=True)

    excluded = prepare_circular_flow_transactions(transactions)
    included = prepare_circular_flow_transactions(
        transactions,
        CircularFlowDetectionConfig(include_self_loops=True),
    )

    assert "TXN_CF_SELF_LOOP" not in set(excluded["transaction_id"])
    assert "TXN_CF_SELF_LOOP" in set(included["transaction_id"])


def test_preparation_handles_counterparty_edges_by_config() -> None:
    transactions = build_circular_flow_counterparty_transactions_fixture()

    excluded = prepare_circular_flow_transactions(transactions)
    included = prepare_circular_flow_transactions(
        transactions,
        CircularFlowDetectionConfig(include_counterparty_edges=True),
    )

    assert "TXN_CF_COUNTERPARTY_001" not in set(excluded["transaction_id"])
    assert "TXN_CF_COUNTERPARTY_001" in set(included["transaction_id"])
    assert "counterparty" in set(included["target_node_type"])
    assert "CP:CP_CF_001" in set(included["target_account_id"])


def test_edge_builder_returns_expected_columns_and_keeps_parallel_edges() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()
    duplicate = transactions.iloc[[0]].copy()
    duplicate.loc[:, "transaction_id"] = "TXN_CF_2HOP_001_DUP"
    duplicate.loc[:, "transaction_timestamp"] = "2025-01-10 09:30:00"
    transactions = pd.concat([transactions, duplicate], ignore_index=True)

    edges = build_circular_flow_edges(transactions)

    assert tuple(edges.columns) == CIRCULAR_FLOW_EDGE_COLUMNS
    assert len(edges.loc[edges["source_account_id"].eq("ACC_CF_A")]) == 2


def test_preparation_and_edge_builder_do_not_mutate_inputs() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()
    original = transactions.copy(deep=True)

    prepare_circular_flow_transactions(transactions)
    build_circular_flow_edges(transactions)

    pd.testing.assert_frame_equal(transactions, original)
