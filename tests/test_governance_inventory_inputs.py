"""Tests for governance inventory input readers."""

import pandas as pd
import pytest

from graph_aml.governance import (
    GovernanceInventoryInputError,
    read_governance_audit_events,
    read_governance_inventory_inputs,
    read_governance_model_runs,
    read_governance_table_counts,
    read_governance_validation_runs,
)


class FakeEngine:
    pass


def test_governance_input_readers_query_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_read(sql: object, *_: object, **__: object) -> pd.DataFrame:
        calls.append(str(sql))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    engine = FakeEngine()
    read_governance_table_counts(engine)  # type: ignore[arg-type]
    read_governance_audit_events(engine, limit=1)  # type: ignore[arg-type]
    read_governance_model_runs(engine, limit=1)  # type: ignore[arg-type]
    read_governance_validation_runs(engine, limit=1)  # type: ignore[arg-type]
    text = "\n".join(calls)
    assert "pg_stat_user_tables" in text
    assert "governance.audit_events" in text
    assert "governance.model_runs" in text
    assert "governance.supervised_model_runs" in text
    assert "governance.model_comparison_runs" in text
    assert "governance.monitoring_runs" in text
    assert "governance.explainability_runs" in text
    assert ":limit" in text


def test_generic_governance_input_reader_returns_expected_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *_args, **_kwargs: pd.DataFrame())
    payload = read_governance_inventory_inputs(FakeEngine(), limit=5)  # type: ignore[arg-type]
    assert set(payload) == {"table_counts", "audit_events", "model_runs", "validation_runs"}
    assert set(payload["model_runs"]) == {"model_runs", "supervised_model_runs"}
    assert set(payload["validation_runs"]) == {
        "model_comparison_runs",
        "monitoring_runs",
        "explainability_runs",
    }


def test_governance_input_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(GovernanceInventoryInputError):
        read_governance_audit_events(FakeEngine())  # type: ignore[arg-type]


def test_governance_input_readers_validate_limits() -> None:
    with pytest.raises(GovernanceInventoryInputError):
        read_governance_audit_events(FakeEngine(), limit=-1)  # type: ignore[arg-type]
