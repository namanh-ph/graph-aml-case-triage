"""Tests for Neo4j driver lifecycle helpers."""

import pytest

import graph_aml.graph.connection as connection
from graph_aml.graph import (
    GraphConnectionError,
    Neo4jConfig,
    close_neo4j_driver,
    create_neo4j_driver,
    create_verified_neo4j_driver,
    get_neo4j_server_info,
    verify_neo4j_connectivity,
)


class FakeDriver:
    def __init__(self) -> None:
        self.closed = False
        self.verified = False
        self.fail_verify = False

    def close(self) -> None:
        self.closed = True

    def verify_connectivity(self) -> None:
        self.verified = True
        if self.fail_verify:
            raise RuntimeError("no connection")

    def get_server_info(self) -> dict[str, object]:
        return {"agent": "Neo4j/5", "address": "localhost:7687"}


def test_create_neo4j_driver_calls_driver_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_driver = FakeDriver()
    calls: list[dict[str, object]] = []

    def fake_factory(*args: object, **kwargs: object) -> FakeDriver:
        calls.append({"args": args, "kwargs": kwargs})
        return fake_driver

    monkeypatch.setattr(connection.GraphDatabase, "driver", fake_factory)
    config = Neo4jConfig(uri="bolt://test:7687", username="user", password="secret")

    driver = create_neo4j_driver(config)

    assert driver is fake_driver
    assert calls[0]["args"] == ("bolt://test:7687",)
    assert calls[0]["kwargs"]["auth"] == ("user", "secret")  # type: ignore[index]


def test_driver_creation_failures_raise_graph_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_factory(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(connection.GraphDatabase, "driver", fail_factory)

    with pytest.raises(GraphConnectionError):
        create_neo4j_driver(Neo4jConfig(password="secret"))


def test_close_neo4j_driver_calls_close() -> None:
    driver = FakeDriver()

    close_neo4j_driver(driver)  # type: ignore[arg-type]

    assert driver.closed is True


def test_closing_none_is_safe() -> None:
    close_neo4j_driver(None)


def test_verify_neo4j_connectivity_calls_driver_verification() -> None:
    driver = FakeDriver()

    verify_neo4j_connectivity(driver)  # type: ignore[arg-type]

    assert driver.verified is True


def test_verification_failures_raise_graph_connection_error() -> None:
    driver = FakeDriver()
    driver.fail_verify = True

    with pytest.raises(GraphConnectionError):
        verify_neo4j_connectivity(driver)  # type: ignore[arg-type]


def test_create_verified_driver_closes_driver_if_verification_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_driver = FakeDriver()
    fake_driver.fail_verify = True
    monkeypatch.setattr(connection.GraphDatabase, "driver", lambda *args, **kwargs: fake_driver)

    with pytest.raises(GraphConnectionError):
        create_verified_neo4j_driver(Neo4jConfig(password="secret"))

    assert fake_driver.closed is True


def test_get_neo4j_server_info_returns_dictionary() -> None:
    info = get_neo4j_server_info(FakeDriver())  # type: ignore[arg-type]

    assert info["agent"] == "Neo4j/5"


def test_no_driver_is_created_at_import_time() -> None:
    assert hasattr(connection, "create_neo4j_driver")
