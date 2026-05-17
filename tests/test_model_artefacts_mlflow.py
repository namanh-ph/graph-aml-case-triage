"""Tests for model artefact writers and MLflow helper."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from graph_aml.models import (
    AnomalyScorePersistenceResult,
    AnomalyScoreResult,
    IsolationForestModelConfig,
    generate_isolation_forest_artefacts,
    log_isolation_forest_mlflow_run,
    train_isolation_forest_model,
    write_anomaly_score_persistence_summary_json,
    write_anomaly_score_summary_json,
    write_anomaly_scores_csv,
    write_anomaly_scores_json,
    write_isolation_forest_training_summary_json,
)


def scores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1"],
            "anomaly_score": [95.0],
            "anomaly_score_raw": [-0.1],
            "is_anomaly": [True],
            "anomaly_rank": [1],
            "risk_band": ["high"],
        }
    )


def training_result():
    frame = pd.DataFrame(
        {"account_id": [f"A{i}" for i in range(5)], "f1": range(5), "f2": range(5)}
    )
    return train_isolation_forest_model(
        frame,
        IsolationForestModelConfig(min_training_rows=5, n_estimators=5, mlflow_enabled=False),
        trained_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_artefact_writers_create_files(tmp_path: Path) -> None:
    training = training_result()
    result = AnomalyScoreResult(scores=scores(), summary={"row_count": 1})
    assert write_anomaly_scores_csv(scores(), tmp_path / "scores.csv").is_file()
    assert write_anomaly_scores_json(scores(), tmp_path / "scores.json").is_file()
    assert write_isolation_forest_training_summary_json(training, tmp_path / "train.json").is_file()
    assert write_anomaly_score_summary_json({"row_count": 1}, tmp_path / "summary.json").is_file()
    assert write_anomaly_score_persistence_summary_json(
        AnomalyScorePersistenceResult(),
        tmp_path / "persist.json",
    ).is_file()
    paths = generate_isolation_forest_artefacts(
        training,
        result,
        AnomalyScorePersistenceResult(),
        tmp_path / "nested",
    )
    assert {"scores_csv", "scores_json", "training_summary_json", "score_summary_json"}.issubset(
        paths
    )
    assert all(path.is_file() for path in paths.values())


def test_mlflow_helper_does_nothing_when_disabled() -> None:
    training = training_result()
    result = AnomalyScoreResult(scores=scores(), summary={"row_count": 1})
    assert (
        log_isolation_forest_mlflow_run(
            training,
            result,
            IsolationForestModelConfig(mlflow_enabled=False),
        )
        is None
    )


def test_mlflow_helper_logs_when_monkeypatched(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class FakeRun:
        info = SimpleNamespace(run_id="run-123")

        def __enter__(self) -> "FakeRun":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    fake_mlflow = SimpleNamespace(
        set_experiment=lambda name: calls.append(f"experiment:{name}"),
        start_run=lambda run_name=None: FakeRun(),
        log_param=lambda key, value: calls.append(f"param:{key}"),
        log_metric=lambda key, value: calls.append(f"metric:{key}"),
        log_artifact=lambda path: calls.append(f"artifact:{Path(path).name}"),
    )
    monkeypatch.setitem(__import__("sys").modules, "mlflow", fake_mlflow)
    training = training_result()
    result = AnomalyScoreResult(scores=scores(), summary={"row_count": 1})
    path = tmp_path / "artifact.txt"
    path.write_text("x", encoding="utf-8")
    run_id = log_isolation_forest_mlflow_run(
        training,
        result,
        IsolationForestModelConfig(mlflow_enabled=True),
        {"x": path},
    )
    assert run_id == "run-123"
    assert any(call.startswith("param:") for call in calls)
    assert any(call.startswith("metric:") for call in calls)
