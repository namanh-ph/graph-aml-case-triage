"""Tests for end-to-end security workflow and audit persistence."""

import pandas as pd
import pytest

from graph_aml.security import (
    SecretsScanConfig,
    SecurityControlConfig,
    SecurityPersistenceError,
    run_and_persist_security_controls,
    write_security_control_audit_event,
)
from graph_aml.security.persistence import SecurityControlPersistenceResult


class FakeConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: object, _params: object | None = None) -> None:
        self.statements.append(str(statement))
        if _params is not None:
            self.statements.append(str(_params))


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self) -> "FakeEngine":
        return self

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *_args: object) -> None:
        return None


def test_workflow_reads_builds_writes_and_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    engine = FakeEngine()
    config = SecurityControlConfig(
        secrets_scan=SecretsScanConfig(root_dirs=(str(tmp_path),)),
    )
    config = type(config)(
        security_name=config.security_name,
        security_version=config.security_version,
        sensitive_fields=config.sensitive_fields,
        masking=config.masking,
        permissions=config.permissions,
        export_controls=config.export_controls,
        secrets_scan=config.secrets_scan,
        audit_integrity=config.audit_integrity,
        persistence=type(config.persistence)(
            write_database=True,
            write_artefacts=True,
            write_audit=True,
            artefact_output_dir=str(tmp_path),
        ),
    )
    monkeypatch.setattr(
        "graph_aml.security.inputs.read_security_inputs",
        lambda *_args, **_kwargs: {
            "table_columns": pd.DataFrame(
                [{"schema_name": "aml", "table_name": "cases", "column_name": "case_id"}]
            ),
            "audit_events": pd.DataFrame(
                [
                    {
                        "event_type": "x",
                        "component": "c",
                        "action": "a",
                        "status": "success",
                        "run_id": "r",
                        "created_at": "2026-01-01",
                    }
                ]
            ),
        },
    )
    result, persisted = run_and_persist_security_controls(engine, config)
    assert result.security_run_id
    assert persisted.persisted
    assert any("governance.audit_events" in statement for statement in engine.connection.statements)
    assert (tmp_path / "security_control_report.md").exists()


def test_audit_writer_uses_expected_event_type() -> None:
    engine = FakeEngine()
    write_security_control_audit_event(
        engine,
        SecurityControlPersistenceResult(security_run_id="run", security_version="v"),
    )
    assert "security_controls" in "\n".join(engine.connection.statements)


def test_audit_writer_failures_raise() -> None:
    class BadEngine:
        def begin(self) -> "BadEngine":
            raise RuntimeError("boom")

    with pytest.raises(SecurityPersistenceError):
        write_security_control_audit_event(
            BadEngine(),  # type: ignore[arg-type]
            SecurityControlPersistenceResult(security_run_id="run"),
        )
