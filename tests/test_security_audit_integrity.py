"""Tests for audit integrity checks."""

import pandas as pd
import pytest

from graph_aml.security import (
    AUDIT_INTEGRITY_COLUMNS,
    AuditIntegrityError,
    run_audit_integrity_checks,
)


def _audit() -> pd.DataFrame:
    return pd.DataFrame(
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
    )


def test_audit_integrity_passes_when_valid() -> None:
    result = run_audit_integrity_checks(_audit(), security_run_id="run")
    assert tuple(result.columns) == AUDIT_INTEGRITY_COLUMNS
    assert int(result["issue_count"].sum()) == 0


def test_audit_integrity_reports_missing_status_and_duplicates() -> None:
    missing = pd.DataFrame({"event_type": ["x"]})
    assert run_audit_integrity_checks(missing)["issue_count"].max() > 0
    bad = pd.concat([_audit(), _audit()], ignore_index=True)
    bad.loc[0, "status"] = "unexpected"
    result = run_audit_integrity_checks(bad)
    assert int(result["issue_count"].sum()) > 0


def test_audit_integrity_rejects_malformed_inputs() -> None:
    with pytest.raises(AuditIntegrityError):
        run_audit_integrity_checks({"bad": "input"})  # type: ignore[arg-type]
