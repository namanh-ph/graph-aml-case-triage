"""Tests for deterministic smoke seed helpers."""

import pytest

from graph_aml.database.exceptions import DatabaseResetRefusedError, DatabaseSeedError
from graph_aml.database.seed import (
    delete_smoke_seed_data,
    read_delete_smoke_seed_data_sql,
    read_seed_smoke_data_sql,
    seed_smoke_data,
)


class FakeEngine:
    pass


def test_read_seed_smoke_data_sql_contains_deterministic_ids() -> None:
    sql = read_seed_smoke_data_sql()

    assert "CUST_SMOKE_001" in sql
    assert "ACC_SMOKE_001" in sql
    assert "TXN_SMOKE_001" in sql


def test_read_delete_smoke_seed_data_sql_returns_targeted_delete_sql() -> None:
    sql = read_delete_smoke_seed_data_sql()

    assert "DELETE FROM aml.case_alerts" in sql
    assert "LIKE 'CASE_SMOKE_%'" in sql


def test_seed_smoke_data_executes_seed_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return 24

    monkeypatch.setattr("graph_aml.database.seed.read_seed_smoke_data_sql", lambda: "seed sql")
    monkeypatch.setattr("graph_aml.database.seed.execute_sql", fake_execute_sql)

    assert seed_smoke_data(FakeEngine()) == {"seed_statements_executed": 24}
    assert calls == ["seed sql"]


def test_delete_smoke_seed_data_requires_confirmation() -> None:
    with pytest.raises(DatabaseResetRefusedError):
        delete_smoke_seed_data(FakeEngine(), confirm=False)


def test_delete_smoke_seed_data_executes_cleanup_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_execute_sql(engine: FakeEngine, sql: str) -> int:
        calls.append(sql)
        return 15

    monkeypatch.setattr(
        "graph_aml.database.seed.read_delete_smoke_seed_data_sql",
        lambda: "delete seed sql",
    )
    monkeypatch.setattr("graph_aml.database.seed.execute_sql", fake_execute_sql)

    assert delete_smoke_seed_data(FakeEngine(), confirm=True) == {
        "delete_seed_statements_executed": 15
    }
    assert calls == ["delete seed sql"]


def test_seed_smoke_data_raises_seed_error_when_execution_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_execute_sql(engine: FakeEngine, sql: str) -> int:
        raise RuntimeError("seed failed")

    monkeypatch.setattr("graph_aml.database.seed.read_seed_smoke_data_sql", lambda: "seed sql")
    monkeypatch.setattr("graph_aml.database.seed.execute_sql", fail_execute_sql)

    with pytest.raises(DatabaseSeedError):
        seed_smoke_data(FakeEngine())


def test_seed_sql_is_idempotent() -> None:
    assert "ON CONFLICT" in read_seed_smoke_data_sql()


def test_cleanup_sql_is_targeted_only() -> None:
    cleanup_sql = read_delete_smoke_seed_data_sql().upper()

    assert "DROP TABLE" not in cleanup_sql
    assert "DROP SCHEMA" not in cleanup_sql
    assert "TRUNCATE" not in cleanup_sql


def test_seed_helpers_do_not_attempt_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoConnectionEngine:
        def connect(self) -> None:
            pytest.fail("seed helpers should not call connect directly")

    monkeypatch.setattr("graph_aml.database.seed.read_seed_smoke_data_sql", lambda: "seed sql")
    monkeypatch.setattr("graph_aml.database.seed.execute_sql", lambda engine, sql: 1)

    assert seed_smoke_data(NoConnectionEngine()) == {"seed_statements_executed": 1}
