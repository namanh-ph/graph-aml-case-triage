"""Tests for graph utility summary helpers."""

import json

from graph_aml.graph import summarise_graph_constraints, summarise_neo4j_health


def test_health_summary_handles_success_payloads() -> None:
    summary = summarise_neo4j_health(
        {
            "status": "ok",
            "database": "neo4j",
            "connectivity_verified": True,
            "query_ok": True,
        }
    )

    assert summary == {
        "status": "ok",
        "database": "neo4j",
        "connectivity_verified": True,
        "query_ok": True,
    }


def test_health_summary_handles_empty_payloads() -> None:
    summary = summarise_neo4j_health({})

    assert summary["status"] == "unknown"
    assert summary["connectivity_verified"] is False
    assert summary["query_ok"] is False


def test_constraint_summary_counts_constraints_and_extracts_names_and_labels() -> None:
    summary = summarise_graph_constraints(
        [
            {
                "name": "constraint_account_account_id_unique",
                "labelsOrTypes": ["Account"],
            },
            {
                "name": "constraint_customer_customer_id_unique",
                "labelsOrTypes": ["Customer"],
            },
        ]
    )

    assert summary["constraint_count"] == 2
    assert summary["constraint_names"] == [
        "constraint_account_account_id_unique",
        "constraint_customer_customer_id_unique",
    ]
    assert summary["labels"] == ["Account", "Customer"]


def test_constraint_summary_handles_empty_inputs() -> None:
    summary = summarise_graph_constraints([])

    assert summary["constraint_count"] == 0
    assert summary["constraint_names"] == []
    assert summary["labels"] == []


def test_summaries_are_json_serialisable() -> None:
    json.dumps(summarise_neo4j_health({}), sort_keys=True)
    json.dumps(summarise_graph_constraints([]), sort_keys=True)
