"""Tests for case generation audit events."""

import pytest

from graph_aml.cases import (
    CasePersistenceError,
    CasePersistenceResult,
    write_case_generation_audit_event,
)


class FakeConnection:
    def __init__(self) -> None:
        self.params = None

    def execute(self, statement, params=None):  # noqa: ANN001
        self.params = params


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


def test_case_audit_event_payload() -> None:
    engine = FakeEngine()
    write_case_generation_audit_event(
        engine,
        CasePersistenceResult(cases_persisted=2, case_alert_links_persisted=3, case_version="v1"),
    )
    params = engine.connection.params
    assert params["event_type"] == "case_generation"
    assert params["component"] == "cases"
    assert params["action"] == "persist_generated_cases"
    assert "cases_persisted" in params["details"]
    assert "case_alert_links_persisted" in params["details"]
    assert "v1" in params["details"]


def test_case_audit_failures_raise() -> None:
    with pytest.raises(CasePersistenceError):
        write_case_generation_audit_event(FakeEngine(fail=True), CasePersistenceResult())
