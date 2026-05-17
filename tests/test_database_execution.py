"""Tests for trusted SQL execution utilities."""

from pathlib import Path

import pytest

from graph_aml.database.exceptions import DatabaseExecutionError
from graph_aml.database.execution import execute_sql, execute_sql_file, split_sql_statements
from graph_aml.database.schemas import read_create_schemas_sql
from graph_aml.database.tables import read_create_tables_sql


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.statements: list[str] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> None:
        if self.fail:
            raise RuntimeError("execution failed")
        self.statements.append(str(statement))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection(fail=fail)

    def begin(self) -> FakeConnection:
        return self.connection


def test_split_sql_statements_returns_simple_statements() -> None:
    assert split_sql_statements("SELECT 1; SELECT 2;") == ["SELECT 1", "SELECT 2"]


def test_split_sql_statements_ignores_blank_statements() -> None:
    assert split_sql_statements("SELECT 1;\n;\n  ;") == ["SELECT 1"]


def test_split_sql_statements_handles_comments_for_project_ddl() -> None:
    sql = "-- comment\nSELECT 1;\n/* block comment */\nSELECT 'a;b';"

    assert split_sql_statements(sql) == [
        "-- comment\nSELECT 1",
        "/* block comment */\nSELECT 'a;b'",
    ]


def test_execute_sql_executes_expected_number_of_statements() -> None:
    engine = FakeEngine()

    count = execute_sql(engine, "SELECT 1; SELECT 2;")

    assert count == 2
    assert len(engine.connection.statements) == 2


def test_execute_sql_file_reads_file_and_executes(tmp_path: Path) -> None:
    sql_file = tmp_path / "script.sql"
    sql_file.write_text("SELECT 1; SELECT 2;", encoding="utf-8")
    engine = FakeEngine()

    assert execute_sql_file(engine, sql_file) == 2


def test_execute_sql_file_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        execute_sql_file(FakeEngine(), tmp_path / "missing.sql")


def test_execute_sql_raises_database_execution_error_on_failure() -> None:
    with pytest.raises(DatabaseExecutionError):
        execute_sql(FakeEngine(fail=True), "SELECT 1;")


def test_existing_project_ddl_files_split_into_non_empty_statements() -> None:
    statements = split_sql_statements(read_create_schemas_sql() + read_create_tables_sql())

    assert statements
    assert all(statement.strip() for statement in statements)
