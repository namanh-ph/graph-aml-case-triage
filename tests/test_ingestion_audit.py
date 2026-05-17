"""Tests for raw ingestion audit event writing."""

import json

import pytest

from graph_aml.ingestion import IngestionAuditError, write_ingestion_audit_event


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, dict[str, object]]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object, parameters: dict[str, object]) -> None:
        if self.fail:
            raise RuntimeError("audit failed")
        self.executions.append((str(statement), parameters))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection(fail=fail)

    def begin(self) -> FakeConnection:
        return self.connection


def test_write_ingestion_audit_event_inserts_audit_row() -> None:
    engine = FakeEngine()

    write_ingestion_audit_event(
        engine,
        dataset_id="dataset",
        dataset_version="version",
        source_system="reference",
        source_file="dataset_metadata.json",
        row_counts={"transactions": 10},
        status="completed",
    )

    assert "INSERT INTO governance.audit_events" in engine.connection.executions[0][0]


def test_audit_details_include_dataset_and_counts() -> None:
    engine = FakeEngine()

    write_ingestion_audit_event(
        engine,
        dataset_id="dataset",
        dataset_version="version",
        source_system="reference",
        source_file="dataset_metadata.json",
        row_counts={"transactions": 10},
        status="completed",
    )

    details = json.loads(str(engine.connection.executions[0][1]["details"]))
    assert details["dataset_id"] == "dataset"
    assert details["dataset_version"] == "version"
    assert details["source_file"] == "dataset_metadata.json"
    assert details["row_counts"] == {"transactions": 10}


def test_audit_event_uses_raw_ingestion_event_type() -> None:
    engine = FakeEngine()

    write_ingestion_audit_event(
        engine,
        "dataset",
        "version",
        "reference",
        "dataset_metadata.json",
        {"transactions": 10},
        "completed",
    )

    assert engine.connection.executions[0][1]["event_type"] == "raw_ingestion"


def test_audit_event_uses_ingestion_component() -> None:
    engine = FakeEngine()

    write_ingestion_audit_event(
        engine,
        "dataset",
        "version",
        "reference",
        "dataset_metadata.json",
        {"transactions": 10},
        "completed",
    )

    assert engine.connection.executions[0][1]["component"] == "ingestion"


def test_audit_failure_raises_ingestion_audit_error() -> None:
    with pytest.raises(IngestionAuditError):
        write_ingestion_audit_event(
            FakeEngine(fail=True),
            "dataset",
            "version",
            "reference",
            "dataset_metadata.json",
            {"transactions": 10},
            "failed",
        )
