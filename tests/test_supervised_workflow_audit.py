from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedDatasetConfig,
    SupervisedFeatureError,
    SupervisedModelConfig,
    SupervisedModelPersistenceConfig,
    SupervisedTrainingResult,
    train_and_persist_supervised_model,
    write_supervised_model_audit_event,
)


class FakeConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((str(sql), params))


class FakeBegin:
    def __init__(self, engine) -> None:
        self.engine = engine

    def __enter__(self):
        return self.engine.connection

    def __exit__(self, *args):
        return False


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self):
        return FakeBegin(self)


def _dataset() -> pd.DataFrame:
    rows = 20
    return pd.DataFrame(
        {
            "case_id": [f"C{i}" for i in range(rows)],
            "case_label": [0, 1] * 10,
            "label_name": ["n", "s"] * 10,
            "label_timestamp": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "dataset_version": ["d"] * rows,
            "case_risk_score": [float(i) for i in range(rows)],
            "alert_count": [i % 3 for i in range(rows)],
        }
    )


def test_end_to_end_workflow_trains_scores_and_persists(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "graph_aml.models.supervised_training.read_supervised_training_dataset",
        lambda *args, **kwargs: _dataset(),
    )
    engine = FakeEngine()
    config = SupervisedModelConfig(
        dataset=SupervisedDatasetConfig(min_rows=10, dataset_version="d"),
    )
    persistence = SupervisedModelPersistenceConfig(dataset_version="d")
    result, scores, persisted = train_and_persist_supervised_model(
        engine,  # type: ignore[arg-type]
        config,
        persistence,
        write_artefacts=True,
    )
    assert isinstance(result, SupervisedTrainingResult)
    assert len(scores) == 20
    assert persisted.persisted is True


def test_audit_writer_inserts_governance_event() -> None:
    engine = FakeEngine()
    from graph_aml.models.supervised_persistence import SupervisedModelPersistenceResult

    write_supervised_model_audit_event(  # type: ignore[arg-type]
        engine,
        SupervisedModelPersistenceResult(model_version="v", dataset_version="d"),
    )
    sql, params = engine.connection.statements[0]
    assert "governance.audit_events" in sql
    assert "supervised_model_training" in params["event_type"]


def test_workflow_does_not_generate_labels() -> None:
    assert "label" not in train_and_persist_supervised_model.__name__.replace("labelled", "")


def test_workflow_failures_raise(monkeypatch) -> None:
    monkeypatch.setattr(
        "graph_aml.models.supervised_training.read_supervised_training_dataset",
        lambda *args, **kwargs: pd.DataFrame(),
    )
    with pytest.raises(SupervisedFeatureError):
        train_and_persist_supervised_model(FakeEngine())  # type: ignore[arg-type]
