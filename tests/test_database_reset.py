"""Tests for explicit database reset helpers."""

from pathlib import Path

import pytest

from graph_aml.database.exceptions import DatabaseResetRefusedError
from graph_aml.database.reset import drop_core_tables, drop_database_schemas, reset_database


class FakeEngine:
    pass


def test_reset_database_requires_confirmation() -> None:
    with pytest.raises(DatabaseResetRefusedError):
        reset_database(FakeEngine(), confirm=False)


def test_drop_core_tables_requires_confirmation() -> None:
    with pytest.raises(DatabaseResetRefusedError):
        drop_core_tables(FakeEngine(), confirm=False)


def test_drop_database_schemas_requires_confirmation() -> None:
    with pytest.raises(DatabaseResetRefusedError):
        drop_database_schemas(FakeEngine(), confirm=False)


def test_reset_database_executes_sql_in_expected_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    counts = {
        "drop tables": 21,
        "drop schemas": 5,
        "create schemas": 10,
        "create tables": 80,
    }

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return counts[sql]

    monkeypatch.setattr("graph_aml.database.reset.read_drop_tables_sql", lambda: "drop tables")
    monkeypatch.setattr("graph_aml.database.reset.read_drop_schemas_sql", lambda: "drop schemas")
    monkeypatch.setattr(
        "graph_aml.database.reset.read_create_schemas_sql",
        lambda: "create schemas",
    )
    monkeypatch.setattr("graph_aml.database.reset.read_create_tables_sql", lambda: "create tables")
    monkeypatch.setattr("graph_aml.database.reset.execute_sql", fake_execute_sql)

    summary = reset_database(FakeEngine(), confirm=True)

    assert calls == ["drop tables", "drop schemas", "create schemas", "create tables"]
    assert summary == {
        "drop_table_statements_executed": 21,
        "drop_schema_statements_executed": 5,
        "create_schema_statements_executed": 10,
        "create_table_statements_executed": 80,
    }


def test_drop_core_tables_executes_drop_table_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return 21

    monkeypatch.setattr("graph_aml.database.reset.read_drop_tables_sql", lambda: "drop tables")
    monkeypatch.setattr("graph_aml.database.reset.execute_sql", fake_execute_sql)

    assert drop_core_tables(FakeEngine(), confirm=True) == 21
    assert calls == ["drop tables"]


def test_drop_database_schemas_executes_drop_schema_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return 5

    monkeypatch.setattr("graph_aml.database.reset.read_drop_schemas_sql", lambda: "drop schemas")
    monkeypatch.setattr("graph_aml.database.reset.execute_sql", fake_execute_sql)

    assert drop_database_schemas(FakeEngine(), confirm=True) == 5
    assert calls == ["drop schemas"]


def test_reset_utility_does_not_execute_seed_sql() -> None:
    source = Path("src/graph_aml/database/reset.py").read_text(encoding="utf-8")

    assert "seed_smoke_data" not in source
    assert "read_seed_smoke_data_sql" not in source


def test_reset_utility_does_not_attempt_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoConnectionEngine:
        def connect(self) -> None:
            pytest.fail("reset helpers should not call connect directly")

    monkeypatch.setattr("graph_aml.database.reset.read_drop_tables_sql", lambda: "drop tables")
    monkeypatch.setattr("graph_aml.database.reset.execute_sql", lambda engine, sql: 1)

    assert drop_core_tables(NoConnectionEngine(), confirm=True) == 1
