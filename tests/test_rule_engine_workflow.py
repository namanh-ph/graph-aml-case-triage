"""Tests for the full staged unified rule engine workflow."""

import pytest

from graph_aml.rules import (
    DEFAULT_RULE_ORDER,
    RULE_STRUCTURING,
    RuleEngineError,
    RuleEngineExecutionResult,
    RuleEngineRunConfig,
    RuleExecutionResult,
    combine_rule_execution_results,
    run_rule_engine_from_staged,
)


class FakeEngine:
    pass


def _no_engine_audit(*args: object, **kwargs: object) -> None:
    return None


def _engine_result(persisted: bool = False) -> RuleEngineExecutionResult:
    return combine_rule_execution_results(
        [
            RuleExecutionResult(
                RULE_STRUCTURING,
                "Structuring",
                "structuring",
                alerts_generated=1,
                alerts_persisted=1 if persisted else 0,
                persisted=persisted,
            )
        ],
        persisted=persisted,
    )


def test_run_rule_engine_from_staged_uses_supplied_run_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, ...]] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda engine, rule_keys, **kwargs: seen.append(tuple(rule_keys)) or _engine_result(),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,)),
    )

    assert seen == [(RULE_STRUCTURING,)]


def test_it_loads_default_config_when_no_run_config_is_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, ...]] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda engine, rule_keys, **kwargs: seen.append(tuple(rule_keys)) or _engine_result(),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(FakeEngine())

    assert seen == [DEFAULT_RULE_ORDER]


def test_it_runs_selected_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda *a, **k: calls.append(1) or _engine_result(),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,)),
    )

    assert calls == [1]


def test_it_preserves_individual_rule_audit_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda engine, rule_keys, **kwargs: seen.append(kwargs["write_audit"]) or _engine_result(),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,), write_audit=True),
    )

    assert seen == [True]


def test_it_writes_engine_level_audit_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda *a, **k: _engine_result(),
    )
    monkeypatch.setattr(
        "graph_aml.rules.engine.write_rule_engine_audit_event",
        lambda *a, **k: calls.append(1),
    )

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,)),
    )

    assert calls == [1]


def test_it_skips_engine_level_audit_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda *a, **k: _engine_result(),
    )
    monkeypatch.setattr(
        "graph_aml.rules.engine.write_rule_engine_audit_event",
        lambda *a, **k: calls.append(1),
    )

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,)),
        write_engine_audit=False,
    )

    assert calls == []


def test_it_skips_all_audit_when_run_config_disables_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda engine, rule_keys, **kwargs: seen.append(kwargs["write_audit"]) or _engine_result(),
    )
    monkeypatch.setattr(
        "graph_aml.rules.engine.write_rule_engine_audit_event",
        lambda *a, **k: pytest.fail("engine audit should be skipped"),
    )

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,), write_audit=False),
    )

    assert seen == [False]


def test_it_passes_persistence_setting_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[bool] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda engine, rule_keys, **kwargs: seen.append(kwargs["persist"]) or _engine_result(True),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,), persist_alerts=True),
    )

    assert seen == [True]


def test_it_passes_artefact_setting_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[bool] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda engine, rule_keys, **kwargs: (
            seen.append(kwargs["write_artefacts"]) or _engine_result()
        ),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,), write_artefacts=False),
    )

    assert seen == [False]


def test_it_returns_rule_engine_execution_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda *a, **k: _engine_result(),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    result = run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,)),
    )

    assert isinstance(result, RuleEngineExecutionResult)


def test_it_does_not_persist_alerts_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda *a, **k: calls.append(1) or _engine_result(True),
    )
    monkeypatch.setattr("graph_aml.rules.engine.write_rule_engine_audit_event", _no_engine_audit)

    run_rule_engine_from_staged(
        FakeEngine(),
        RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,), persist_alerts=True),
    )

    assert calls == [1]


def test_failures_raise_rule_engine_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.rules.engine.load_individual_rule_configs", lambda **k: {})
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rules_from_staged",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuleEngineError):
        run_rule_engine_from_staged(
            FakeEngine(),
            RuleEngineRunConfig(enabled_rules=(RULE_STRUCTURING,)),
        )
