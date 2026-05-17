"""Tests for release readiness workflow and audit persistence."""

from __future__ import annotations

import pandas as pd

from graph_aml.release import run_and_persist_release_readiness
from graph_aml.release.persistence import write_release_readiness_audit_event
from tests.test_release_workflow import _config


class _Connection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement, params=None) -> None:
        self.statements.append(str(statement))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _Engine:
    def __init__(self) -> None:
        self.connection = _Connection()

    def begin(self) -> _Connection:
        return self.connection


def test_release_workflow_writes_artefacts_and_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# Overview\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "model_card.md").write_text("card", encoding="utf-8")
    (tmp_path / "Makefile").write_text("check:\n\tpython -m pytest\n", encoding="utf-8")

    def fake_read_sql(query, engine, params=None):
        return pd.DataFrame([{"count": 1}])

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    engine = _Engine()
    config = _config()
    result, persisted = run_and_persist_release_readiness(
        engine,  # type: ignore[arg-type]
        config,
        write_artefacts=True,
    )

    assert result.release_run_id
    assert persisted is not None and persisted.persisted
    assert (tmp_path / "reports" / "model_validation" / "release_readiness_report.md").exists()
    assert any("governance.audit_events" in sql for sql in engine.connection.statements)


def test_release_audit_writer_inserts_audit_event() -> None:
    engine = _Engine()
    from graph_aml.release.persistence import ReleasePersistenceResult

    write_release_readiness_audit_event(
        engine,  # type: ignore[arg-type]
        ReleasePersistenceResult(release_run_id="run", release_version="v1"),
    )
    assert any("governance.audit_events" in sql for sql in engine.connection.statements)
