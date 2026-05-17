from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.labels import (
    LabelDatasetBuildResult,
    LabelPersistenceResult,
    build_and_persist_label_datasets,
    write_label_generation_audit_event,
)


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[object, object]] = []

    def execute(self, sql, params=None):  # noqa: ANN001
        self.executed.append((sql, params))
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self):
        engine = self

        class Context:
            def __enter__(self_inner):
                return engine.connection

            def __exit__(self_inner, exc_type, exc, tb):  # noqa: ANN001
                return False

        return Context()


def _inputs() -> dict[str, pd.DataFrame]:
    return {
        "cases": pd.DataFrame(
            {
                "case_id": ["C1"],
                "primary_account_id": ["A1"],
                "created_at": [pd.Timestamp("2026-01-01", tz="UTC")],
            }
        ),
        "lifecycle_events": pd.DataFrame(
            {
                "action_id": ["E1"],
                "case_id": ["C1"],
                "to_status": ["Closed suspicious"],
                "action_type": ["close_suspicious"],
                "analyst_id": ["u1"],
                "decision_reason": ["reason"],
                "comment": ["comment"],
                "action_timestamp": [pd.Timestamp("2026-01-02", tz="UTC")],
            }
        ),
        "case_entities": pd.DataFrame(columns=["case_id", "entity_type", "entity_id"]),
        "case_risk_scores": pd.DataFrame(columns=["case_id"]),
        "account_features": pd.DataFrame(columns=["account_id"]),
        "account_risk_scores": pd.DataFrame(columns=["account_id"]),
        "graph_features": pd.DataFrame(columns=["account_id"]),
        "anomaly_scores": pd.DataFrame(columns=["account_id"]),
    }


def test_end_to_end_label_workflow_reads_inputs(monkeypatch) -> None:
    called = {"read": False}

    def fake_read(engine, config, limit=None):  # noqa: ANN001
        called["read"] = True
        return _inputs()

    monkeypatch.setattr("graph_aml.labels.dataset.read_label_inputs", fake_read)
    result, persisted = build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert called["read"] is True
    assert isinstance(result, LabelDatasetBuildResult)
    assert isinstance(persisted, LabelPersistenceResult)


def test_workflow_builds_case_labels(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: _inputs(),
    )
    result, _ = build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert len(result.case_labels) == 1


def test_workflow_builds_account_labels(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: _inputs(),
    )
    result, _ = build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert result.summary["account_label_count"] == 1


def test_workflow_builds_supervised_datasets(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: _inputs(),
    )
    result, _ = build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert result.case_dataset is not None


def test_workflow_persists_labels(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: _inputs(),
    )
    _, persisted = build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert persisted.persisted is True


def test_workflow_returns_build_and_persistence_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: _inputs(),
    )
    result, persisted = build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert isinstance(result, LabelDatasetBuildResult)
    assert isinstance(persisted, LabelPersistenceResult)


def test_audit_writer_inserts_into_governance_audit_events() -> None:
    engine = FakeEngine()
    write_label_generation_audit_event(
        engine, LabelPersistenceResult(label_version="v1", dataset_version="d1")
    )
    assert "governance.audit_events" in str(engine.connection.executed[0][0])


def test_audit_details_include_versions() -> None:
    engine = FakeEngine()
    write_label_generation_audit_event(
        engine, LabelPersistenceResult(label_version="v1", dataset_version="d1")
    )
    params = engine.connection.executed[0][1]
    assert "v1" in params["details"]
    assert "d1" in params["details"]


def test_workflow_does_not_train_models(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: _inputs(),
    )
    assert "train" not in build_and_persist_label_datasets.__name__


def test_failures_raise_controlled_label_exceptions(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.labels.dataset.read_label_inputs",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(Exception) as exc_info:
        build_and_persist_label_datasets(FakeEngine())  # type: ignore[arg-type]
    assert exc_info.value.__class__.__name__.startswith("Label")
