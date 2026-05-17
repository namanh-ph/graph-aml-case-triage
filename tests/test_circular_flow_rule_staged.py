"""Tests for staged circular flow alert rule readers and runner."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.rules import (
    CircularFlowDetectionConfig,
    RuleDataReadError,
    read_circular_flow_rule_inputs,
    run_circular_flow_rule_from_staged,
)
from graph_aml.rules.staged import read_staged_transactions_for_rules
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_accounts_fixture,
    build_circular_flow_three_hop_transactions_fixture,
)


class FakeEngine:
    pass


def _inputs(*args: object, **kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        build_circular_flow_three_hop_transactions_fixture(),
        build_circular_flow_accounts_fixture(),
    )


def _path(*args: object, **kwargs: object) -> Path:
    return Path("reports/model_validation/fake.json")


def _no_audit(*args: object, **kwargs: object) -> None:
    return None


def test_read_circular_flow_rule_inputs_returns_transactions_and_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.rules.staged.read_staged_transactions_for_rules",
        lambda *args, **kwargs: build_circular_flow_three_hop_transactions_fixture(),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.read_staged_accounts_for_rules",
        lambda *args, **kwargs: build_circular_flow_accounts_fixture(),
    )

    transactions, accounts = read_circular_flow_rule_inputs(FakeEngine())

    assert len(transactions) == 3
    assert len(accounts) > 0


def test_run_circular_flow_rule_from_staged_runs_detection_and_alert_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_alerts_json", _path)

    summary = run_circular_flow_rule_from_staged(FakeEngine())

    assert summary["cycles_detected"] == 1
    assert summary["alerts_generated"] == 1


def test_runner_writes_artefacts_only_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_detections_json",
        lambda *a, **k: calls.append("detections_json") or Path("fake.json"),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_detections_csv",
        lambda *a, **k: calls.append("detections_csv") or Path("fake.csv"),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_summary_json",
        lambda *a, **k: calls.append("summary_json") or Path("fake_summary.json"),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_alerts_json",
        lambda *a, **k: calls.append("alerts_json") or Path("fake_alerts.json"),
    )

    run_circular_flow_rule_from_staged(FakeEngine(), write_artefacts=False)
    run_circular_flow_rule_from_staged(FakeEngine(), write_artefacts=True)

    assert calls == ["detections_json", "detections_csv", "summary_json", "alerts_json"]


def test_runner_persists_alerts_only_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_alerts_json", _path)
    monkeypatch.setattr(
        "graph_aml.rules.staged.persist_alerts",
        lambda *args, **kwargs: calls.append(1) or {"alerts_upserted": 1},
    )

    run_circular_flow_rule_from_staged(FakeEngine(), persist=False)
    run_circular_flow_rule_from_staged(FakeEngine(), persist=True)

    assert calls == [1]


def test_runner_writes_audit_only_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_alerts_json", _path)

    run_circular_flow_rule_from_staged(FakeEngine(), write_audit=False)
    run_circular_flow_rule_from_staged(FakeEngine(), write_audit=True)

    assert len(calls) == 1


def test_runner_uses_circular_flow_rule_audit_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_alerts_json", _path)

    run_circular_flow_rule_from_staged(FakeEngine())

    assert calls[0]["action"] == "run_circular_flow_rule"


def test_runner_does_not_call_detection_only_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_alerts_json", _path)
    monkeypatch.setattr(
        "graph_aml.rules.staged.run_circular_flow_detection_from_staged",
        lambda *args, **kwargs: pytest.fail("rule runner must not call detection-only workflow"),
    )

    run_circular_flow_rule_from_staged(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))


def test_staged_read_failures_raise_rule_data_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read_sql_query(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)

    with pytest.raises(RuleDataReadError):
        read_staged_transactions_for_rules(FakeEngine())


def test_runner_accepts_custom_detection_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_alerts_json", _path)

    summary = run_circular_flow_rule_from_staged(
        FakeEngine(),
        detection_config=CircularFlowDetectionConfig(max_cycle_hops=3),
    )

    assert summary["alerts_generated"] == 1
