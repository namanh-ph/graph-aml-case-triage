"""Tests for end-to-end case generation workflow."""

import pandas as pd
import pytest

from graph_aml.cases import CaseGenerationError, generate_and_persist_cases
from graph_aml.cases.generation import CaseGenerationResult
from graph_aml.cases.persistence import CasePersistenceResult


class FakeEngine:
    pass


def test_case_workflow_reads_generates_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    generated = CaseGenerationResult(
        cases=pd.DataFrame({"case_id": ["C1"]}),
        case_alerts=pd.DataFrame(),
        case_entities=pd.DataFrame(),
        groups=pd.DataFrame(),
    )
    persisted = CasePersistenceResult(cases_persisted=1)

    monkeypatch.setattr(
        "graph_aml.cases.inputs.read_case_inputs",
        lambda engine, config, limit=None: calls.append(limit) or {"alerts": pd.DataFrame()},
    )
    monkeypatch.setattr(
        "graph_aml.cases.generation.generate_cases_from_inputs",
        lambda inputs, config=None: generated,
    )
    monkeypatch.setattr(
        "graph_aml.cases.persistence.persist_cases",
        lambda engine, result, config=None, extra_metadata=None: persisted,
    )
    result = generate_and_persist_cases(FakeEngine(), limit=7)
    assert result == (generated, persisted)
    assert calls == [7]


def test_case_workflow_does_not_create_engines_or_run_other_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.cases.inputs.read_case_inputs", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        "graph_aml.cases.generation.generate_cases_from_inputs",
        lambda *args, **kwargs: CaseGenerationResult(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        ),
    )
    monkeypatch.setattr(
        "graph_aml.cases.persistence.persist_cases",
        lambda *args, **kwargs: CasePersistenceResult(),
    )
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    generate_and_persist_cases(FakeEngine())


def test_case_workflow_failures_raise_controlled_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.cases.inputs.read_case_inputs",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(CaseGenerationError):
        generate_and_persist_cases(FakeEngine())
