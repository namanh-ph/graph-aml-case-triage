"""Tests for graph node mapping."""

import pandas as pd

from graph_aml.graph import (
    build_account_nodes,
    build_alert_nodes,
    build_all_graph_nodes,
    build_counterparty_nodes,
    build_country_nodes,
    build_customer_nodes,
    build_transaction_nodes,
)


def test_customer_nodes_are_built_and_deduplicated() -> None:
    frame = pd.DataFrame(
        [
            {"customer_id": "C1", "customer_type": "individual", "customer_segment": "retail"},
            {"customer_id": "C1", "customer_type": "individual", "customer_segment": "retail"},
            {"customer_id": None, "customer_type": "missing"},
        ]
    )

    assert build_customer_nodes(frame) == [
        {"customer_id": "C1", "customer_type": "individual", "segment": "retail"}
    ]


def test_account_nodes_are_built_with_account_ids() -> None:
    rows = build_account_nodes(
        pd.DataFrame([{"account_id": "A1", "customer_id": "C1", "account_status": "open"}])
    )

    assert rows[0]["account_id"] == "A1"
    assert rows[0]["status"] == "open"


def test_transaction_nodes_are_built_with_transaction_ids() -> None:
    rows = build_transaction_nodes(
        pd.DataFrame(
            [
                {
                    "transaction_id": "T1",
                    "transaction_timestamp": "2024-01-01T00:00:00Z",
                    "amount": "12.50",
                }
            ]
        )
    )

    assert rows[0]["transaction_id"] == "T1"
    assert rows[0]["amount"] == 12.5


def test_counterparty_nodes_use_table_and_transaction_inference() -> None:
    rows = build_counterparty_nodes(
        pd.DataFrame([{"counterparty_id": "CP1", "counterparty_name": "Acme"}]),
        pd.DataFrame([{"counterparty_id": "CP2", "destination_country": "GB"}]),
    )

    assert [row["counterparty_id"] for row in rows] == ["CP1", "CP2"]


def test_country_nodes_use_table_and_inference() -> None:
    rows = build_country_nodes(
        pd.DataFrame([{"country_code": "AU", "country_name": "Australia"}]),
        pd.DataFrame([{"origin_country": "US", "destination_country": "GB"}]),
        pd.DataFrame([{"country_code": "SG"}]),
    )

    assert [row["country_code"] for row in rows] == ["AU", "GB", "SG", "US"]


def test_alert_nodes_preserve_evidence_ids() -> None:
    rows = build_alert_nodes(
        pd.DataFrame([{"alert_id": "AL1", "risk_score_rule": 90, "evidence_ids": ["T1", "T2"]}])
    )

    assert rows == [{"alert_id": "AL1", "risk_score_rule": 90.0, "evidence_ids": ["T1", "T2"]}]


def test_node_ordering_is_deterministic_and_inputs_are_not_mutated() -> None:
    frame = pd.DataFrame([{"account_id": "B"}, {"account_id": "A"}])
    original = frame.copy(deep=True)

    rows = build_account_nodes(frame)

    assert [row["account_id"] for row in rows] == ["A", "B"]
    pd.testing.assert_frame_equal(frame, original)


def test_build_all_graph_nodes_returns_all_labels() -> None:
    nodes = build_all_graph_nodes(
        {
            "customers": pd.DataFrame([{"customer_id": "C1"}]),
            "accounts": pd.DataFrame([{"account_id": "A1"}]),
            "transactions": pd.DataFrame([{"transaction_id": "T1"}]),
            "counterparties": pd.DataFrame([{"counterparty_id": "CP1"}]),
            "countries": pd.DataFrame([{"country_code": "AU"}]),
            "alerts": pd.DataFrame([{"alert_id": "AL1"}]),
        }
    )

    assert set(nodes) == {"Customer", "Account", "Transaction", "Counterparty", "Country", "Alert"}
