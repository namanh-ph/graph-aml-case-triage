"""Tests for staging pipeline orchestration."""

import pandas as pd
import pytest

from graph_aml.staging.exceptions import StagingTransformationError
from graph_aml.staging.pipeline import run_staging_pipeline, transform_raw_to_staging_frames


class FakeEngine:
    pass


def test_transform_raw_to_staging_frames_reads_raw_dataset_and_transforms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        "graph_aml.staging.pipeline.read_raw_dataset",
        lambda engine, limit=None: calls.append("read") or {"countries": pd.DataFrame()},
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.transform_raw_dataset",
        lambda raw_dataset: calls.append("transform") or _staging_dataset(),
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.validate_staging_dataset",
        lambda staging_dataset: calls.append("validate"),
    )

    transform_raw_to_staging_frames(FakeEngine())

    assert calls == ["read", "transform", "validate"]


def test_transform_raw_to_staging_frames_returns_all_expected_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.read_raw_dataset", lambda engine, limit=None: {}
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.transform_raw_dataset",
        lambda raw_dataset: _staging_dataset(),
    )
    monkeypatch.setattr("graph_aml.staging.pipeline.validate_staging_dataset", lambda dataset: None)

    output = transform_raw_to_staging_frames(FakeEngine())

    assert set(output) == {
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    }


def test_run_staging_pipeline_calls_steps_in_expected_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        "graph_aml.staging.pipeline.transform_raw_to_staging_frames",
        lambda engine, limit=None, validate=True: calls.append("frames") or _staging_dataset(),
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.load_staging_dataset",
        lambda engine, staging_dataset: calls.append("load") or {"countries": 1},
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.write_staging_audit_event",
        lambda engine, row_counts, status, metadata=None: calls.append("audit"),
    )

    row_counts = run_staging_pipeline(FakeEngine())

    assert calls == ["frames", "load", "audit"]
    assert row_counts == {"countries": 1}


def test_run_staging_pipeline_skips_audit_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        "graph_aml.staging.pipeline.transform_raw_to_staging_frames",
        lambda engine, limit=None, validate=True: _staging_dataset(),
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.load_staging_dataset",
        lambda engine, staging_dataset: {"countries": 1},
    )
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.write_staging_audit_event",
        lambda *args, **kwargs: calls.append("audit"),
    )

    run_staging_pipeline(FakeEngine(), write_audit=False)

    assert calls == []


def test_run_staging_pipeline_passes_validate_false(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[bool] = []

    def fake_frames(engine, limit=None, validate=True):
        seen.append(validate)
        return _staging_dataset()

    monkeypatch.setattr("graph_aml.staging.pipeline.transform_raw_to_staging_frames", fake_frames)
    monkeypatch.setattr(
        "graph_aml.staging.pipeline.load_staging_dataset",
        lambda engine, staging_dataset: {"countries": 1},
    )

    run_staging_pipeline(FakeEngine(), validate=False, write_audit=False)

    assert seen == [False]


def test_pipeline_failures_propagate_as_staging_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_transform(engine, limit=None, validate=True):
        raise StagingTransformationError("bad staging data")

    monkeypatch.setattr(
        "graph_aml.staging.pipeline.transform_raw_to_staging_frames", fail_transform
    )

    with pytest.raises(StagingTransformationError):
        run_staging_pipeline(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert callable(run_staging_pipeline)


def _staging_dataset() -> dict[str, pd.DataFrame]:
    return {
        "countries": pd.DataFrame(),
        "customers": pd.DataFrame(),
        "accounts": pd.DataFrame(),
        "counterparties": pd.DataFrame(),
        "devices": pd.DataFrame(),
        "transactions": pd.DataFrame(),
    }
