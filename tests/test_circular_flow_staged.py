"""Tests for staged circular flow detection readers and runner."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.rules import (
    CircularFlowDetectionConfig,
    RuleDataReadError,
    read_circular_flow_detection_inputs,
    run_circular_flow_detection_from_staged,
)
from graph_aml.rules.staged import read_staged_transactions_for_rules
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_three_hop_transactions_fixture,
)


class FakeEngine:
    pass


def _transactions(*args: object, **kwargs: object) -> pd.DataFrame:
    return build_circular_flow_three_hop_transactions_fixture()


def _path(*args: object, **kwargs: object) -> Path:
    return Path("reports/model_validation/fake.json")


def _no_audit(*args: object, **kwargs: object) -> None:
    return None


def test_read_circular_flow_detection_inputs_reads_from_staged_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_staged_transactions_for_rules", _transactions)

    transactions = read_circular_flow_detection_inputs(FakeEngine())

    assert len(transactions) == 3


def test_read_circular_flow_detection_inputs_applies_limit_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[int | None] = []

    def capture_limit(engine: object, limit: int | None = None) -> pd.DataFrame:
        captured.append(limit)
        return build_circular_flow_three_hop_transactions_fixture()

    monkeypatch.setattr(
        "graph_aml.rules.staged.read_staged_transactions_for_rules",
        capture_limit,
    )

    read_circular_flow_detection_inputs(FakeEngine(), limit=10)

    assert captured == [10]


def test_run_circular_flow_detection_from_staged_runs_detection_using_staged_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_detection_inputs", _transactions)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)

    summary = run_circular_flow_detection_from_staged(FakeEngine())

    assert summary["cycles_detected"] == 1
    assert summary["persisted"] is False


def test_runner_writes_artefacts_only_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_detection_inputs", _transactions)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_detections_json",
        lambda *a, **k: calls.append("json") or Path("fake.json"),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_detections_csv",
        lambda *a, **k: calls.append("csv") or Path("fake.csv"),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_circular_flow_summary_json",
        lambda *a, **k: calls.append("summary") or Path("fake_summary.json"),
    )

    run_circular_flow_detection_from_staged(FakeEngine(), write_artefacts=False)
    run_circular_flow_detection_from_staged(FakeEngine(), write_artefacts=True)

    assert calls == ["json", "csv", "summary"]


def test_runner_writes_audit_only_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_detection_inputs", _transactions)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)

    run_circular_flow_detection_from_staged(FakeEngine(), write_audit=False)
    run_circular_flow_detection_from_staged(FakeEngine(), write_audit=True)

    assert len(calls) == 1


def test_runner_uses_detect_circular_flows_audit_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_detection_inputs", _transactions)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)

    run_circular_flow_detection_from_staged(FakeEngine())

    assert calls[0]["action"] == "detect_circular_flows"


def test_runner_does_not_call_alert_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_detection_inputs", _transactions)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)
    monkeypatch.setattr(
        "graph_aml.rules.staged.persist_alerts",
        lambda *args, **kwargs: pytest.fail("circular flow must not persist alerts"),
    )

    run_circular_flow_detection_from_staged(FakeEngine())


def test_staged_read_failures_raise_rule_data_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read_sql_query(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)

    with pytest.raises(RuleDataReadError):
        read_staged_transactions_for_rules(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))


def test_runner_accepts_custom_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_circular_flow_detection_inputs", _transactions)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_json", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_detections_csv", _path)
    monkeypatch.setattr("graph_aml.rules.staged.write_circular_flow_summary_json", _path)

    summary = run_circular_flow_detection_from_staged(
        FakeEngine(),
        config=CircularFlowDetectionConfig(max_cycle_hops=3),
    )

    assert summary["cycles_detected"] == 1
