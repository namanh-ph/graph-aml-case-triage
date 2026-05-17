"""Tests for case evidence persistence."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseEvidencePersistenceConfig,
    CaseEvidencePersistenceError,
    CaseEvidencePersistenceResult,
    build_case_evidence_pack_upsert_sql,
    build_case_explanation_upsert_sql,
    persist_case_evidence,
    prepare_case_evidence_for_persistence,
    upsert_case_evidence_packs,
    validate_case_evidence_persistence_config,
)
from tests.fixtures.case_evidence import evidence_result


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


def test_persistence_config_and_preparation() -> None:
    validate_case_evidence_persistence_config(CaseEvidencePersistenceConfig())
    with pytest.raises(CaseEvidencePersistenceError):
        CaseEvidencePersistenceConfig(evidence_version="")
    with pytest.raises(CaseEvidencePersistenceError):
        CaseEvidencePersistenceConfig(batch_size=0)
    prepared = prepare_case_evidence_for_persistence(evidence_result())
    assert set(prepared) == {"evidence_packs", "explanations"}
    assert "updated_at" in prepared["evidence_packs"].columns
    assert "updated_at" in prepared["explanations"].columns


def test_upsert_sql_and_workflow() -> None:
    evidence_sql = build_case_evidence_pack_upsert_sql()
    explanation_sql = build_case_explanation_upsert_sql()
    assert "INSERT INTO aml.case_evidence_packs" in evidence_sql
    assert "INSERT INTO aml.case_explanations" in explanation_sql
    assert ":case_id" in evidence_sql
    assert "ON CONFLICT" in evidence_sql
    assert "created_at = EXCLUDED.created_at" not in evidence_sql
    assert upsert_case_evidence_packs(FakeEngine(), pd.DataFrame()) == 0
    result = persist_case_evidence(
        FakeEngine(),
        evidence_result(),
        CaseEvidencePersistenceConfig(write_audit=False),
    )
    assert isinstance(result, CaseEvidencePersistenceResult)
    assert result.evidence_packs_persisted == 1
    assert result.explanations_persisted == 1


def test_persistence_skips_audit_and_does_not_create_engines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    persist_case_evidence(
        FakeEngine(), evidence_result(), CaseEvidencePersistenceConfig(write_audit=False)
    )
    with pytest.raises(CaseEvidencePersistenceError):
        persist_case_evidence(FakeEngine(fail=True), evidence_result())
