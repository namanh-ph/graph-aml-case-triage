"""Tests for parameterised Cypher execution helpers."""

import pytest

from graph_aml.graph import (
    GraphExecutionError,
    run_cypher_batch,
    run_cypher_read,
    run_cypher_scalar,
    run_cypher_write,
)


class FakeRecord:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def data(self) -> dict[str, object]:
        return self.payload


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self.session = session

    def run(self, query: str, parameters: dict[str, object]) -> list[FakeRecord]:
        self.session.runs.append((query, parameters))
        if self.session.fail:
            raise RuntimeError("query failed")
        return [FakeRecord(row) for row in self.session.rows]


class FakeSession:
    def __init__(self, rows: list[dict[str, object]] | None = None, fail: bool = False) -> None:
        self.rows = [{"ok": 1}] if rows is None else rows
        self.fail = fail
        self.runs: list[tuple[str, dict[str, object]]] = []
        self.closed = False
        self.read_called = False
        self.write_called = False

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.closed = True

    def execute_read(self, callback: object, *args: object) -> object:
        self.read_called = True
        return callback(FakeTransaction(self), *args)  # type: ignore[operator]

    def execute_write(self, callback: object, *args: object) -> object:
        self.write_called = True
        return callback(FakeTransaction(self), *args)  # type: ignore[operator]


class FakeDriver:
    def __init__(self, session: FakeSession) -> None:
        self.session_obj = session
        self.session_calls: list[dict[str, object]] = []

    def session(self, **kwargs: object) -> FakeSession:
        self.session_calls.append(kwargs)
        return self.session_obj


def test_run_cypher_read_opens_session_and_returns_dictionaries() -> None:
    session = FakeSession(rows=[{"value": 1}])
    rows = run_cypher_read(FakeDriver(session), "RETURN $value AS value", {"value": 1})

    assert rows == [{"value": 1}]
    assert session.read_called is True
    assert session.closed is True


def test_run_cypher_write_opens_session_and_returns_dictionaries() -> None:
    session = FakeSession(rows=[{"created": 2}])
    rows = run_cypher_write(FakeDriver(session), "CREATE (n) RETURN 2 AS created")

    assert rows == [{"created": 2}]
    assert session.write_called is True
    assert session.closed is True


def test_run_cypher_scalar_returns_first_scalar_value() -> None:
    assert run_cypher_scalar(FakeDriver(FakeSession(rows=[{"ok": 1}])), "RETURN 1 AS ok") == 1


def test_run_cypher_scalar_returns_none_for_empty_results() -> None:
    assert run_cypher_scalar(FakeDriver(FakeSession(rows=[])), "RETURN 1 AS ok") is None


def test_run_cypher_batch_returns_zero_for_empty_rows() -> None:
    assert run_cypher_batch(FakeDriver(FakeSession()), "UNWIND $rows AS row RETURN row", []) == 0


def test_run_cypher_batch_sends_rows_in_batches() -> None:
    session = FakeSession(rows=[])
    attempted = run_cypher_batch(
        FakeDriver(session),
        "UNWIND $rows AS row RETURN row",
        [{"id": 1}, {"id": 2}, {"id": 3}],
        batch_size=2,
    )

    assert attempted == 3
    assert [len(parameters["rows"]) for _, parameters in session.runs] == [2, 1]


def test_invalid_query_strings_raise_graph_execution_error() -> None:
    with pytest.raises(GraphExecutionError):
        run_cypher_read(FakeDriver(FakeSession()), "  ")


def test_invalid_batch_size_raises_graph_execution_error() -> None:
    with pytest.raises(GraphExecutionError):
        run_cypher_batch(FakeDriver(FakeSession()), "RETURN 1", [{"id": 1}], batch_size=0)


def test_execution_failures_raise_graph_execution_error() -> None:
    with pytest.raises(GraphExecutionError):
        run_cypher_read(FakeDriver(FakeSession(fail=True)), "RETURN 1")


def test_database_name_is_passed_to_session() -> None:
    driver = FakeDriver(FakeSession())

    run_cypher_read(driver, "RETURN 1", database="neo4j")

    assert driver.session_calls == [{"database": "neo4j"}]
