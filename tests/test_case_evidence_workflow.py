"""Tests for high-level case evidence workflow."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CASE_EVIDENCE_PACK_COLUMNS,
    CASE_EXPLANATION_COLUMNS,
    CaseEvidenceBuildError,
    CaseEvidencePersistenceConfig,
    CaseEvidencePersistenceResult,
    build_and_persist_case_evidence,
    build_case_evidence_packs,
)
from tests.fixtures.case_evidence import evidence_inputs


class FakeEngine:
    def begin(self):
        class Context:
            def __enter__(self_inner):
                return object()

            def __exit__(self_inner, exc_type, exc, tb):  # noqa: ANN001
                return False

        return Context()


def test_high_level_evidence_build_outputs_expected_frames() -> None:
    result = build_case_evidence_packs(evidence_inputs())
    assert len(result.evidence_packs) == 1
    assert len(result.explanations) == 1
    assert tuple(result.evidence_packs.columns) == CASE_EVIDENCE_PACK_COLUMNS
    assert tuple(result.explanations.columns) == CASE_EXPLANATION_COLUMNS
    assert result.summary["case_count"] == 1


def test_build_and_persist_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_read(engine, config=None, case_ids=None, limit=None):  # noqa: ANN001
        calls["limit"] = limit
        calls["case_ids"] = case_ids
        return evidence_inputs()

    def fake_persist(engine, result, config=None, extra_metadata=None):  # noqa: ANN001
        calls["persisted"] = True
        return CaseEvidencePersistenceResult(evidence_packs_persisted=1, explanations_persisted=1)

    monkeypatch.setattr("graph_aml.cases.evidence_inputs.read_case_evidence_inputs", fake_read)
    monkeypatch.setattr("graph_aml.cases.evidence_persistence.persist_case_evidence", fake_persist)
    result, persistence = build_and_persist_case_evidence(
        FakeEngine(),
        persistence_config=CaseEvidencePersistenceConfig(write_audit=False),
        case_ids=["CASE_001"],
        limit=10,
    )
    assert len(result.evidence_packs) == 1
    assert persistence.evidence_packs_persisted == 1
    assert calls["limit"] == 10
    assert calls["case_ids"] == ["CASE_001"]
    assert calls["persisted"]


def test_workflow_does_not_create_engines_or_run_unrelated_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    monkeypatch.setattr(
        "graph_aml.cases.evidence_inputs.read_case_evidence_inputs",
        lambda *args, **kwargs: evidence_inputs(),
    )
    monkeypatch.setattr(
        "graph_aml.cases.evidence_persistence.persist_case_evidence",
        lambda *args, **kwargs: CaseEvidencePersistenceResult(),
    )
    build_and_persist_case_evidence(FakeEngine())
    with pytest.raises(CaseEvidenceBuildError):
        build_case_evidence_packs({"cases": pd.DataFrame({"not_case_id": ["x"]})})
