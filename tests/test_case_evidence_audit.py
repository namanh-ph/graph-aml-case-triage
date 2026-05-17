"""Tests for case evidence audit event writing."""

import pytest

from graph_aml.cases import (
    CaseEvidencePersistenceError,
    CaseEvidencePersistenceResult,
    write_case_evidence_audit_event,
)


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


def test_case_evidence_audit_writer_payload() -> None:
    engine = FakeEngine()
    write_case_evidence_audit_event(
        engine,
        CaseEvidencePersistenceResult(
            evidence_packs_persisted=1,
            explanations_persisted=1,
            evidence_version="case_evidence_v1",
            explanation_version="deterministic_explanation_v1",
        ),
    )
    params = engine.connection.executions[0][1]
    assert params["event_type"] == "case_evidence_generation"
    assert params["component"] == "cases"
    assert params["action"] == "persist_case_evidence_packs"
    assert "evidence_packs_persisted" in params["details"]
    assert "explanations_persisted" in params["details"]
    assert "case_evidence_v1" in params["details"]
    assert "deterministic_explanation_v1" in params["details"]


def test_case_evidence_audit_failures_raise() -> None:
    with pytest.raises(CaseEvidencePersistenceError):
        write_case_evidence_audit_event(FakeEngine(fail=True), CaseEvidencePersistenceResult())
