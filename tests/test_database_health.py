"""Tests for database health utilities."""

import pytest

from graph_aml.database.exceptions import DatabaseConnectionError
from graph_aml.database.health import (
    check_database_connection,
    get_database_server_version,
    get_existing_schemas,
    get_existing_tables,
)


class FakeResult:
    def __init__(self, scalar: object | None = None, rows: list[tuple[str]] | None = None) -> None:
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one(self) -> object:
        return self.scalar

    def __iter__(self) -> object:
        return iter(self.rows)


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object, parameters: dict[str, str] | None = None) -> FakeResult:
        if self.fail:
            raise RuntimeError("connection failed")
        sql = str(statement)
        if "SELECT 1" in sql:
            return FakeResult(scalar=1)
        if "SELECT version()" in sql:
            return FakeResult(scalar="PostgreSQL 16")
        if "information_schema.schemata" in sql:
            return FakeResult(rows=[("staging",), ("raw",)])
        if "information_schema.tables" in sql:
            assert parameters == {"schema_name": "staging"}
            return FakeResult(rows=[("transactions",), ("accounts",)])
        raise AssertionError(f"Unexpected SQL: {sql}")


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def connect(self) -> FakeConnection:
        return FakeConnection(fail=self.fail)


def test_check_database_connection_returns_true_on_success() -> None:
    assert check_database_connection(FakeEngine())


def test_check_database_connection_raises_on_failure() -> None:
    with pytest.raises(DatabaseConnectionError):
        check_database_connection(FakeEngine(fail=True))


def test_get_database_server_version_returns_string() -> None:
    assert get_database_server_version(FakeEngine()) == "PostgreSQL 16"


def test_get_existing_schemas_returns_sorted_tuple() -> None:
    assert get_existing_schemas(FakeEngine()) == ("raw", "staging")


def test_get_existing_tables_returns_sorted_tuple() -> None:
    assert get_existing_tables(FakeEngine(), "staging") == ("accounts", "transactions")


def test_health_functions_do_not_print_output(capsys: pytest.CaptureFixture[str]) -> None:
    check_database_connection(FakeEngine())
    get_database_server_version(FakeEngine())
    get_existing_schemas(FakeEngine())
    get_existing_tables(FakeEngine(), "staging")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
