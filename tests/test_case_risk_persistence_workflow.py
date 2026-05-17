"""Tests for case risk persistence workflow and audit."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseRiskPersistenceError,
    CaseRiskScorePersistenceConfig,
    CaseRiskScorePersistenceResult,
    persist_case_risk_scores,
    update_case_risk_snapshot,
    upsert_case_risk_scores,
    write_case_risk_score_audit_event,
)
from graph_aml.cases.risk_persistence import prepare_case_risk_scores_for_persistence
from tests.fixtures.case_risk import case_risk_score_result


class FakeConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[object, object]] = []

    def execute(self, statement, params=None):  # noqa: ANN001
        self.executions.append((statement, params))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection()
        self.fail = fail

    def begin(self):
        engine = self

        class Context:
            def __enter__(self_inner):
                if engine.fail:
                    raise RuntimeError("boom")
                return engine.connection

            def __exit__(self_inner, exc_type, exc, tb):  # noqa: ANN001
                return False

        return Context()


def test_upsert_and_snapshot_empty_return_zero() -> None:
    assert upsert_case_risk_scores(FakeEngine(), pd.DataFrame()) == 0
    assert update_case_risk_snapshot(FakeEngine(), pd.DataFrame()) == 0


def test_upsert_and_snapshot_write_batches() -> None:
    prepared = prepare_case_risk_scores_for_persistence(case_risk_score_result())
    engine = FakeEngine()
    assert upsert_case_risk_scores(engine, prepared, batch_size=1) == 1
    assert update_case_risk_snapshot(engine, prepared, batch_size=1) == 1


def test_persist_scores_returns_result_and_skips_audit() -> None:
    result = persist_case_risk_scores(
        FakeEngine(),
        case_risk_score_result(),
        CaseRiskScorePersistenceConfig(write_audit=False, update_case_snapshot=False),
    )
    assert isinstance(result, CaseRiskScorePersistenceResult)
    assert result.rows_persisted == 1
    assert result.case_snapshots_updated == 0


def test_audit_writer_payload() -> None:
    engine = FakeEngine()
    write_case_risk_score_audit_event(
        engine,
        CaseRiskScorePersistenceResult(rows_persisted=1, score_version="v1"),
    )
    params = engine.connection.executions[0][1]
    assert params["event_type"] == "case_risk_scoring"
    assert params["component"] == "cases"
    assert params["action"] == "persist_case_risk_scores"
    assert "rows_persisted" in params["details"]
    assert "v1" in params["details"]


def test_persistence_failures_raise() -> None:
    with pytest.raises(CaseRiskPersistenceError):
        persist_case_risk_scores(FakeEngine(fail=True), case_risk_score_result())


def test_persistence_does_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    persist_case_risk_scores(
        FakeEngine(),
        case_risk_score_result(),
        CaseRiskScorePersistenceConfig(write_audit=False, update_case_snapshot=False),
    )
