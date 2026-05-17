from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedModelPersistenceConfig,
    SupervisedPersistenceError,
    build_supervised_model_run_insert_sql,
    build_supervised_run_id,
    build_supervised_score_upsert_sql,
    validate_supervised_model_persistence_config,
)
from graph_aml.models.supervised_training import SupervisedTrainingResult


def _result() -> SupervisedTrainingResult:
    return SupervisedTrainingResult(
        model_name="m",
        model_version="v",
        model_family="logistic_regression",
        estimator=object(),
        preprocessing_pipeline=object(),
        feature_names=("a",),
        validation_metrics={"precision": 1.0},
        threshold_metrics=pd.DataFrame(),
        top_k_metrics=pd.DataFrame(),
    )


def test_default_persistence_config_is_valid() -> None:
    validate_supervised_model_persistence_config(SupervisedModelPersistenceConfig())


def test_invalid_persistence_config_raises() -> None:
    with pytest.raises(SupervisedPersistenceError):
        validate_supervised_model_persistence_config(
            SupervisedModelPersistenceConfig(batch_size=0)
        )


def test_score_upsert_sql_targets_table_and_uses_conflict() -> None:
    sql = build_supervised_score_upsert_sql()
    assert "INSERT INTO mart.supervised_model_scores" in sql
    assert "ON CONFLICT" in sql
    assert ":entity_id" in sql
    assert "created_at = EXCLUDED.created_at" not in sql


def test_model_run_insert_sql_targets_table() -> None:
    sql = build_supervised_model_run_insert_sql()
    assert "INSERT INTO governance.supervised_model_runs" in sql
    assert ":run_id" in sql


def test_run_id_is_deterministic() -> None:
    assert build_supervised_run_id(_result()) == build_supervised_run_id(_result())


def test_persistence_functions_do_not_create_engines(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    assert build_supervised_score_upsert_sql()
