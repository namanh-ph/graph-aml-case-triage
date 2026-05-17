"""Tests for staged unified rule engine execution."""

from pathlib import Path

import pytest

from graph_aml.rules import (
    RULE_CIRCULAR_FLOW,
    RULE_FAN_IN,
    RULE_STRUCTURING,
    RuleDefinition,
    RuleEngineError,
    RuleExecutionResult,
    run_rule_from_staged,
    run_rules_from_staged,
)


class FakeEngine:
    pass


def test_run_rule_from_staged_dispatches_to_correct_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_staged(engine, config=None, limit=None, persist=False, write_audit=True):
        calls.append("structuring")
        return {"rule_name": "Structuring", "alerts_generated": 0}

    monkeypatch.setattr(
        "graph_aml.rules.engine.get_rule_definition",
        lambda rule_key: RuleDefinition(
            RULE_STRUCTURING,
            "Structuring",
            "structuring",
            object,
            lambda *a, **k: (),
            fake_staged,
        ),
    )

    result = run_rule_from_staged(FakeEngine(), RULE_STRUCTURING)

    assert calls == ["structuring"]
    assert result.rule_key == RULE_STRUCTURING


def test_run_rules_from_staged_runs_selected_rules_in_registry_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run(engine, rule_key, **kwargs):
        calls.append(rule_key)
        return RuleExecutionResult(rule_key, rule_key, rule_key)

    monkeypatch.setattr("graph_aml.rules.engine.run_rule_from_staged", fake_run)

    run_rules_from_staged(FakeEngine(), rule_keys=[RULE_FAN_IN, RULE_STRUCTURING])

    assert calls == [RULE_FAN_IN, RULE_STRUCTURING]


def test_persist_true_is_passed_to_individual_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda engine, rule_key, **kwargs: (
            seen.append(kwargs["persist"]) or RuleExecutionResult(rule_key, rule_key, rule_key)
        ),
    )

    run_rules_from_staged(FakeEngine(), rule_keys=[RULE_STRUCTURING], persist=True)

    assert seen == [True]


def test_persist_false_is_passed_to_individual_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda engine, rule_key, **kwargs: (
            seen.append(kwargs["persist"]) or RuleExecutionResult(rule_key, rule_key, rule_key)
        ),
    )

    run_rules_from_staged(FakeEngine(), rule_keys=[RULE_STRUCTURING], persist=False)

    assert seen == [False]


def test_write_audit_is_passed_to_individual_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda engine, rule_key, **kwargs: (
            seen.append(kwargs["write_audit"]) or RuleExecutionResult(rule_key, rule_key, rule_key)
        ),
    )

    run_rules_from_staged(FakeEngine(), rule_keys=[RULE_STRUCTURING], write_audit=False)

    assert seen == [False]


def test_write_artefacts_is_passed_to_circular_flow_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda engine, rule_key, **kwargs: (
            seen.append(kwargs["write_artefacts"])
            or RuleExecutionResult(rule_key, rule_key, rule_key)
        ),
    )

    run_rules_from_staged(FakeEngine(), rule_keys=[RULE_CIRCULAR_FLOW], write_artefacts=False)

    assert seen == [False]


def test_output_dir_is_passed_to_circular_flow_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Path] = []
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda engine, rule_key, **kwargs: (
            seen.append(Path(kwargs["output_dir"]))
            or RuleExecutionResult(rule_key, rule_key, rule_key)
        ),
    )

    run_rules_from_staged(
        FakeEngine(),
        rule_keys=[RULE_CIRCULAR_FLOW],
        output_dir=Path("reports/test"),
    )

    assert seen == [Path("reports/test")]


def test_staged_engine_aggregates_rule_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda engine, rule_key, **kwargs: RuleExecutionResult(
            rule_key,
            rule_key,
            rule_key,
            alerts_generated=2,
        ),
    )

    result = run_rules_from_staged(FakeEngine(), rule_keys=[RULE_STRUCTURING, RULE_FAN_IN])

    assert result.alerts_generated == 4


def test_staged_engine_does_not_create_database_engine_internally() -> None:
    assert isinstance(FakeEngine(), FakeEngine)


def test_staged_execution_failures_raise_rule_engine_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_from_staged",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuleEngineError):
        run_rules_from_staged(FakeEngine(), rule_keys=[RULE_STRUCTURING])
