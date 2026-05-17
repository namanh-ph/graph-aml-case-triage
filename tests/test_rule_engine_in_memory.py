"""Tests for in-memory unified rule engine execution."""

import pandas as pd
import pytest

from graph_aml.alerts import AlertRecord
from graph_aml.rules import (
    RULE_CIRCULAR_FLOW,
    RULE_FAN_IN,
    RULE_STRUCTURING,
    CircularFlowDetectionConfig,
    CircularFlowRuleConfig,
    RuleDefinition,
    RuleEngineError,
    RuleRegistryError,
    run_rule_in_memory,
    run_rules_in_memory,
)


def _alert(alert_id: str, account_id: str, rule_name: str, typology: str) -> AlertRecord:
    return AlertRecord(
        alert_id=alert_id,
        account_id=account_id,
        customer_id=None,
        rule_name=rule_name,
        typology=typology,
        severity="high",
        risk_score_rule=80.0,
        reason_code="test",
        evidence_ids=(f"TXN_{alert_id}",),
        detection_window_start="2025-01-01T00:00:00+00:00",
        detection_window_end="2025-01-01T01:00:00+00:00",
    )


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.DataFrame({"transaction_id": ["TXN_1"]}), pd.DataFrame({"account_id": ["ACC_1"]})


def test_run_rule_in_memory_dispatches_to_correct_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_runner(transactions, accounts, config=None, model_run_id=None):
        calls.append("structuring")
        return (_alert("A1", "ACC_1", "Structuring", "structuring"),)

    monkeypatch.setattr(
        "graph_aml.rules.engine.get_rule_definition",
        lambda rule_key: RuleDefinition(
            RULE_STRUCTURING,
            "Structuring",
            "structuring",
            object,
            fake_runner,
            lambda *a, **k: {},
        ),
    )

    result = run_rule_in_memory(RULE_STRUCTURING, *_frames())

    assert calls == ["structuring"]
    assert result.alerts_generated == 1


def test_run_rules_in_memory_runs_selected_rules_in_registry_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run(rule_key, transactions, accounts, rule_config=None, model_run_id=None):
        calls.append(rule_key)
        return {
            RULE_STRUCTURING: _result(RULE_STRUCTURING, "Structuring", "structuring"),
            RULE_FAN_IN: _result(RULE_FAN_IN, "Fan-in", "fan_in"),
        }[rule_key]

    monkeypatch.setattr("graph_aml.rules.engine.run_rule_in_memory", fake_run)

    run_rules_in_memory(*_frames(), rule_keys=[RULE_FAN_IN, RULE_STRUCTURING])

    assert calls == [RULE_FAN_IN, RULE_STRUCTURING]


def test_in_memory_execution_does_not_persist_alerts() -> None:
    result = run_rules_in_memory(*_frames(), rule_keys=[])

    assert result.persisted is False
    assert result.alerts_persisted == 0


def test_in_memory_execution_does_not_write_audit_events() -> None:
    result = run_rules_in_memory(*_frames(), rule_keys=[])

    assert result.summary["rules_run"] == []


def test_in_memory_execution_accepts_custom_rule_configs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []

    def fake_run(rule_key, transactions, accounts, rule_config=None, model_run_id=None):
        seen.append(rule_config)
        return _result(rule_key, "Structuring", "structuring")

    monkeypatch.setattr("graph_aml.rules.engine.run_rule_in_memory", fake_run)

    run_rules_in_memory(
        *_frames(),
        rule_keys=[RULE_STRUCTURING],
        rule_configs={RULE_STRUCTURING: object()},
    )

    assert len(seen) == 1


def test_in_memory_execution_handles_circular_flow_configs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_runner(
        transactions,
        accounts,
        detection_config=None,
        alert_config=None,
        model_run_id=None,
    ):
        seen["detection"] = detection_config
        seen["alert"] = alert_config
        return (_alert("CF1", "ACC_A", "Circular flow", "circular_flow"),)

    monkeypatch.setattr(
        "graph_aml.rules.engine.get_rule_definition",
        lambda rule_key: RuleDefinition(
            RULE_CIRCULAR_FLOW,
            "Circular flow",
            "circular_flow",
            object,
            fake_runner,
            lambda *a, **k: {},
            supports_artefacts=True,
        ),
    )
    detection_config = CircularFlowDetectionConfig(max_cycle_hops=3)
    alert_config = CircularFlowRuleConfig(detection_config=detection_config)

    result = run_rule_in_memory(
        RULE_CIRCULAR_FLOW,
        *_frames(),
        rule_config={"detection_config": detection_config, "alert_config": alert_config},
    )

    assert seen == {"detection": detection_config, "alert": alert_config}
    assert result.alerts_generated == 1


def test_in_memory_execution_aggregates_alerts_across_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_in_memory",
        lambda rule_key, *a, **k: _result(rule_key, rule_key, rule_key),
    )

    result = run_rules_in_memory(*_frames(), rule_keys=[RULE_STRUCTURING, RULE_FAN_IN])

    assert result.alerts_generated == 2


def test_in_memory_execution_does_not_mutate_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    transactions, accounts = _frames()
    original_transactions = transactions.copy(deep=True)
    original_accounts = accounts.copy(deep=True)
    monkeypatch.setattr(
        "graph_aml.rules.engine.run_rule_in_memory",
        lambda rule_key, *a, **k: _result(rule_key, rule_key, rule_key),
    )

    run_rules_in_memory(transactions, accounts, rule_keys=[RULE_STRUCTURING])

    pd.testing.assert_frame_equal(transactions, original_transactions)
    pd.testing.assert_frame_equal(accounts, original_accounts)


def test_unknown_rule_keys_raise_registry_error() -> None:
    with pytest.raises(RuleRegistryError):
        run_rule_in_memory("unknown", *_frames())


def test_rule_execution_failures_include_rule_key_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_runner(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "graph_aml.rules.engine.get_rule_definition",
        lambda rule_key: RuleDefinition(
            RULE_STRUCTURING,
            "Structuring",
            "structuring",
            object,
            fail_runner,
            lambda *a, **k: {},
        ),
    )

    with pytest.raises(RuleEngineError, match=RULE_STRUCTURING):
        run_rule_in_memory(RULE_STRUCTURING, *_frames())


def _result(rule_key: str, rule_name: str, typology: str):
    from graph_aml.rules import RuleExecutionResult

    return RuleExecutionResult(
        rule_key,
        rule_name,
        typology,
        alerts=(_alert(f"A_{rule_key}", "ACC_1", rule_name, typology),),
        alerts_generated=1,
    )
