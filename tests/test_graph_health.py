"""Tests for Neo4j health check helpers."""

import json

import pytest

import graph_aml.graph.health as health
from graph_aml.graph import (
    GraphHealthCheckError,
    check_neo4j_database_access,
    check_neo4j_health,
    collect_neo4j_health_summary,
)


class FakeDriver:
    pass


def test_check_neo4j_health_verifies_connectivity_and_runs_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(health, "verify_neo4j_connectivity", lambda driver: calls.append("verify"))
    monkeypatch.setattr(
        health,
        "run_cypher_scalar",
        lambda driver, query, database=None: calls.append(query) or 1,
    )
    monkeypatch.setattr(health, "get_neo4j_server_info", lambda driver: {"agent": "Neo4j/5"})

    payload = check_neo4j_health(FakeDriver(), database="neo4j")  # type: ignore[arg-type]

    assert calls == ["verify", "RETURN 1 AS ok"]
    assert payload["status"] == "ok"
    assert payload["database"] == "neo4j"
    assert payload["connectivity_verified"] is True
    assert payload["query_ok"] is True


def test_database_access_check_returns_query_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "run_cypher_scalar", lambda driver, query, database=None: 1)

    payload = check_neo4j_database_access(FakeDriver(), database="neo4j")  # type: ignore[arg-type]

    assert payload["status"] == "ok"
    assert payload["query_ok"] is True


def test_health_summary_is_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        health,
        "check_neo4j_health",
        lambda driver, database=None: {
            "status": "ok",
            "database": database,
            "connectivity_verified": True,
            "query_ok": True,
            "server_info": {},
        },
    )
    monkeypatch.setattr(
        health,
        "check_neo4j_database_access",
        lambda driver, database=None: {"status": "ok", "database": database, "query_ok": True},
    )

    payload = collect_neo4j_health_summary(FakeDriver(), database="neo4j")  # type: ignore[arg-type]

    json.dumps(payload, sort_keys=True)


def test_failed_health_checks_raise_graph_health_check_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "verify_neo4j_connectivity", lambda driver: None)
    monkeypatch.setattr(health, "run_cypher_scalar", lambda driver, query, database=None: 0)

    with pytest.raises(GraphHealthCheckError):
        check_neo4j_health(FakeDriver())  # type: ignore[arg-type]


def test_health_functions_do_not_create_drivers_internally() -> None:
    assert hasattr(health, "check_neo4j_health")
    assert "create_neo4j_driver" not in health.check_neo4j_health.__code__.co_names
