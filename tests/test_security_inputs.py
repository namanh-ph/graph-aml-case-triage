"""Tests for security input readers."""

import pandas as pd
import pytest

from graph_aml.security import (
    SecurityPersistenceError,
    read_security_audit_events,
    read_security_inputs,
    read_security_sample_table,
    read_security_table_columns,
)


class FakeEngine:
    pass


def test_security_input_readers_query_expected_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_read(sql: object, *_args: object, **_kwargs: object) -> pd.DataFrame:
        calls.append(str(sql))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    engine = FakeEngine()
    read_security_table_columns(engine)  # type: ignore[arg-type]
    read_security_audit_events(engine, limit=1)  # type: ignore[arg-type]
    read_security_sample_table(engine, "aml", "cases", limit=1)  # type: ignore[arg-type]
    text = "\n".join(calls)
    assert "information_schema.columns" in text
    assert "governance.audit_events" in text
    assert '"aml"."cases"' in text
    assert ":limit" in text


def test_sample_reader_rejects_unsafe_schema_and_table() -> None:
    with pytest.raises(SecurityPersistenceError):
        read_security_sample_table(FakeEngine(), "public", "cases")  # type: ignore[arg-type]
    with pytest.raises(SecurityPersistenceError):
        read_security_sample_table(FakeEngine(), "aml", "bad;drop")  # type: ignore[arg-type]


def test_generic_security_inputs_return_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *_args, **_kwargs: pd.DataFrame())
    payload = read_security_inputs(FakeEngine(), limit=5)  # type: ignore[arg-type]
    assert set(payload) == {"table_columns", "audit_events"}


def test_security_input_failures_and_invalid_limits_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(SecurityPersistenceError):
        read_security_audit_events(FakeEngine())  # type: ignore[arg-type]
    with pytest.raises(SecurityPersistenceError):
        read_security_audit_events(FakeEngine(), limit=0)  # type: ignore[arg-type]
