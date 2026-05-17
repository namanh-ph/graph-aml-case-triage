"""Tests for end-to-end case risk scoring workflow."""

import pandas as pd
import pytest

from graph_aml.cases import CaseRiskComputationError, compute_and_persist_case_risk_scores
from graph_aml.cases.risk_persistence import CaseRiskScorePersistenceResult
from graph_aml.cases.risk_scoring import CaseRiskScoreResult


class FakeEngine:
    pass


def test_case_risk_workflow_reads_scores_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    score_result = CaseRiskScoreResult(pd.DataFrame({"case_id": ["C1"]}), pd.DataFrame())
    persist_result = CaseRiskScorePersistenceResult(rows_persisted=1)
    monkeypatch.setattr(
        "graph_aml.cases.risk_inputs.read_case_risk_inputs",
        lambda engine, config, limit=None: calls.append(limit) or {},
    )
    monkeypatch.setattr(
        "graph_aml.cases.risk_scoring.compute_case_risk_scores_from_inputs",
        lambda inputs, config=None, score_date=None: score_result,
    )
    monkeypatch.setattr(
        "graph_aml.cases.risk_persistence.persist_case_risk_scores",
        lambda engine, result, config=None, extra_metadata=None: persist_result,
    )
    assert compute_and_persist_case_risk_scores(FakeEngine(), limit=3) == (
        score_result,
        persist_result,
    )
    assert calls == [3]


def test_case_risk_workflow_does_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.cases.risk_inputs.read_case_risk_inputs", lambda *a, **k: {})
    monkeypatch.setattr(
        "graph_aml.cases.risk_scoring.compute_case_risk_scores_from_inputs",
        lambda *a, **k: CaseRiskScoreResult(pd.DataFrame(), pd.DataFrame()),
    )
    monkeypatch.setattr(
        "graph_aml.cases.risk_persistence.persist_case_risk_scores",
        lambda *a, **k: CaseRiskScorePersistenceResult(),
    )
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    compute_and_persist_case_risk_scores(FakeEngine())


def test_case_risk_workflow_failures_raise_controlled_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.cases.risk_inputs.read_case_risk_inputs",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(CaseRiskComputationError):
        compute_and_persist_case_risk_scores(FakeEngine())
