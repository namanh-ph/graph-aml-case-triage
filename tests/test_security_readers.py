"""Tests for security readback utilities."""

import json

import pandas as pd
import pytest

from graph_aml.security import (
    SecurityPersistenceError,
    read_audit_integrity_checks,
    read_permission_matrix,
    read_secrets_scan_findings,
    read_security_control_runs,
    read_security_control_summary,
    read_sensitive_field_inventory,
)


class FakeEngine:
    pass


def test_security_readers_query_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_read(sql: object, *_args: object, **_kwargs: object) -> pd.DataFrame:
        calls.append(str(sql))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    engine = FakeEngine()
    read_security_control_runs(engine, security_version="v", limit=1)  # type: ignore[arg-type]
    read_sensitive_field_inventory(
        engine, security_run_id="r", classification="restricted", limit=1
    )  # type: ignore[arg-type]
    read_permission_matrix(engine, security_run_id="r", role="viewer", limit=1)  # type: ignore[arg-type]
    read_secrets_scan_findings(engine, security_run_id="r", allowed=False, limit=1)  # type: ignore[arg-type]
    read_audit_integrity_checks(engine, security_run_id="r", status="fail", limit=1)  # type: ignore[arg-type]
    text = "\n".join(calls)
    for table in (
        "governance.security_control_runs",
        "governance.sensitive_field_inventory",
        "governance.permission_matrix",
        "governance.secrets_scan_findings",
        "governance.audit_integrity_checks",
    ):
        assert table in text
    assert ":security_run_id" in text
    assert ":limit" in text


def test_security_summary_is_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read(sql: object, *_args: object, **_kwargs: object) -> pd.DataFrame:
        text = str(sql)
        if "security_control_runs" in text:
            return pd.DataFrame([{"security_run_id": "run", "security_version": "v"}])
        if "sensitive_field_inventory" in text:
            return pd.DataFrame([{"classification": "restricted"}])
        if "permission_matrix" in text:
            return pd.DataFrame([{"role": "viewer"}])
        if "secrets_scan_findings" in text:
            return pd.DataFrame()
        return pd.DataFrame([{"issue_count": 0}])

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    json.dumps(read_security_control_summary(FakeEngine()), default=str)  # type: ignore[arg-type]


def test_security_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd,
        "read_sql_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(SecurityPersistenceError):
        read_security_control_runs(FakeEngine())  # type: ignore[arg-type]
    with pytest.raises(SecurityPersistenceError):
        read_security_control_runs(FakeEngine(), limit=0)  # type: ignore[arg-type]
