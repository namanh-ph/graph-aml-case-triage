"""Tests for graph relationship mapping."""

import pandas as pd

from graph_aml.graph import (
    build_alert_relationships,
    build_all_graph_relationships,
    build_country_relationships,
    build_owns_relationships,
    build_paid_to_relationships,
    build_received_relationships,
    build_sent_relationships,
)


def test_owns_relationships_are_built_from_customer_and_account_ids() -> None:
    rows = build_owns_relationships(pd.DataFrame([{"customer_id": "C1", "account_id": "A1"}]))

    assert rows == [{"customer_id": "C1", "account_id": "A1"}]


def test_transaction_flow_relationships_are_built() -> None:
    transactions = pd.DataFrame(
        [
            {
                "transaction_id": "T1",
                "sender_account_id": "A1",
                "receiver_account_id": "A2",
                "counterparty_id": "CP1",
                "amount": 100,
            }
        ]
    )

    assert build_sent_relationships(transactions)[0]["account_id"] == "A1"
    assert build_received_relationships(transactions)[0]["account_id"] == "A2"
    assert build_paid_to_relationships(transactions)[0]["counterparty_id"] == "CP1"


def test_country_relationships_are_built_for_entities() -> None:
    rows = build_country_relationships(
        pd.DataFrame([{"customer_id": "C1", "jurisdiction": "AU"}]),
        pd.DataFrame([{"account_id": "A1", "home_country": "GB"}]),
        pd.DataFrame([{"transaction_id": "T1", "destination_country": "US"}]),
        pd.DataFrame([{"counterparty_id": "CP1", "country_code": "SG"}]),
    )

    assert {row["source_label"] for row in rows} == {
        "Customer",
        "Account",
        "Transaction",
        "Counterparty",
    }


def test_alert_relationships_flag_accounts_and_explode_evidence_ids() -> None:
    relationships = build_alert_relationships(
        pd.DataFrame(
            [
                {
                    "alert_id": "AL1",
                    "account_id": "A1",
                    "evidence_ids": ["T1", "T2"],
                    "rule_name": "Structuring",
                    "typology": "structuring",
                }
            ]
        )
    )

    assert relationships["FLAGS_ACCOUNT"] == [
        {
            "alert_id": "AL1",
            "rule_name": "Structuring",
            "typology": "structuring",
            "account_id": "A1",
        }
    ]
    assert [row["transaction_id"] for row in relationships["INVOLVES_TRANSACTION"]] == [
        "T1",
        "T2",
    ]
    assert [row["transaction_id"] for row in relationships["TRIGGERS"]] == ["T1", "T2"]


def test_relationships_are_deduplicated_and_missing_keys_are_dropped() -> None:
    rows = build_owns_relationships(
        pd.DataFrame(
            [
                {"customer_id": "C1", "account_id": "A1"},
                {"customer_id": "C1", "account_id": "A1"},
                {"customer_id": "C2", "account_id": None},
            ]
        )
    )

    assert rows == [{"customer_id": "C1", "account_id": "A1"}]


def test_relationship_ordering_is_deterministic_and_inputs_are_not_mutated() -> None:
    frame = pd.DataFrame(
        [{"customer_id": "C2", "account_id": "A2"}, {"customer_id": "C1", "account_id": "A1"}]
    )
    original = frame.copy(deep=True)

    rows = build_owns_relationships(frame)

    assert [row["customer_id"] for row in rows] == ["C1", "C2"]
    pd.testing.assert_frame_equal(frame, original)


def test_build_all_graph_relationships_returns_expected_groups() -> None:
    relationships = build_all_graph_relationships(
        {
            "customers": pd.DataFrame([{"customer_id": "C1", "jurisdiction": "AU"}]),
            "accounts": pd.DataFrame([{"customer_id": "C1", "account_id": "A1"}]),
            "transactions": pd.DataFrame([{"transaction_id": "T1", "sender_account_id": "A1"}]),
            "counterparties": pd.DataFrame(),
            "alerts": pd.DataFrame(
                [{"alert_id": "AL1", "account_id": "A1", "evidence_ids": ["T1"]}]
            ),
        }
    )

    assert {
        "OWNS",
        "SENT",
        "RECEIVED",
        "PAID_TO",
        "LOCATED_IN",
        "TRIGGERS",
        "FLAGS_ACCOUNT",
        "INVOLVES_TRANSACTION",
    } == set(relationships)
