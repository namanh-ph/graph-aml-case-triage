"""Tests for database initialisation helpers."""

import pytest

from graph_aml.database.exceptions import DatabaseInitialisationError
from graph_aml.database.initialise import (
    create_core_tables,
    create_database_schemas,
    initialise_database,
)


class FakeEngine:
    pass


def test_create_database_schemas_executes_schema_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return 2

    monkeypatch.setattr(
        "graph_aml.database.initialise.read_create_schemas_sql",
        lambda: "schema sql",
    )
    monkeypatch.setattr("graph_aml.database.initialise.execute_sql", fake_execute_sql)

    assert create_database_schemas(FakeEngine()) == 2
    assert calls == ["schema sql"]


def test_create_core_tables_executes_table_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return 3

    monkeypatch.setattr("graph_aml.database.initialise.read_create_tables_sql", lambda: "table sql")
    monkeypatch.setattr("graph_aml.database.initialise.execute_sql", fake_execute_sql)

    assert create_core_tables(FakeEngine()) == 3
    assert calls == ["table sql"]


def test_initialise_database_calls_schema_creation_before_table_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_create_database_schemas(engine: FakeEngine) -> int:
        calls.append("schemas")
        return 10

    def fake_create_core_tables(engine: FakeEngine) -> int:
        calls.append("tables")
        return 20

    monkeypatch.setattr(
        "graph_aml.database.initialise.create_database_schemas",
        fake_create_database_schemas,
    )
    monkeypatch.setattr("graph_aml.database.initialise.create_core_tables", fake_create_core_tables)

    summary = initialise_database(FakeEngine())

    assert calls == ["schemas", "tables"]
    assert summary == {"schema_statements_executed": 10, "table_statements_executed": 20}


def test_initialise_database_raises_initialisation_error_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create_database_schemas(engine: FakeEngine) -> int:
        raise RuntimeError("schema failure")

    monkeypatch.setattr(
        "graph_aml.database.initialise.create_database_schemas",
        fail_create_database_schemas,
    )

    with pytest.raises(DatabaseInitialisationError):
        initialise_database(FakeEngine())


def test_initialise_database_does_not_use_drop_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.database.initialise.create_database_schemas", lambda engine: 1)
    monkeypatch.setattr("graph_aml.database.initialise.create_core_tables", lambda engine: 1)
    monkeypatch.setattr(
        "graph_aml.database.schemas.read_drop_schemas_sql",
        lambda: pytest.fail("drop schema SQL should not be used"),
    )
    monkeypatch.setattr(
        "graph_aml.database.tables.read_drop_tables_sql",
        lambda: pytest.fail("drop table SQL should not be used"),
    )

    assert initialise_database(FakeEngine()) == {
        "schema_statements_executed": 1,
        "table_statements_executed": 1,
    }


def test_initialise_database_does_not_attempt_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("graph_aml.database.initialise.create_database_schemas", lambda value: 1)
    monkeypatch.setattr("graph_aml.database.initialise.create_core_tables", lambda value: 1)

    assert initialise_database(engine)["schema_statements_executed"] == 1
