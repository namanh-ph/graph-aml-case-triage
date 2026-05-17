"""Tests for security control workflow."""

import pandas as pd
import pytest

from graph_aml.security import (
    SecretsScanConfig,
    SecurityControlConfig,
    SecurityControlError,
    build_security_run_id,
    run_security_controls_from_inputs,
)


def _config(tmp_path) -> SecurityControlConfig:
    return SecurityControlConfig(secrets_scan=SecretsScanConfig(root_dirs=(str(tmp_path),)))


def _inputs() -> dict[str, object]:
    return {
        "table_columns": pd.DataFrame(
            [
                {"schema_name": "aml", "table_name": "cases", "column_name": "case_id"},
                {"schema_name": "aml", "table_name": "cases", "column_name": "customer_name"},
            ]
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
    }


def test_security_run_id_is_deterministic() -> None:
    timestamp = pd.Timestamp("2026-01-01T00:00:00Z")
    assert build_security_run_id(generated_at=timestamp) == build_security_run_id(
        generated_at=timestamp
    )


def test_security_workflow_builds_all_outputs(tmp_path) -> None:
    inputs = _inputs()
    original = {
        key: value.copy(deep=True)
        for key, value in inputs.items()
        if isinstance(value, pd.DataFrame)
    }
    result = run_security_controls_from_inputs(inputs, _config(tmp_path))
    assert not result.sensitive_fields.empty
    assert not result.permission_matrix.empty
    assert "unallowed_secret_finding_count" in result.summary
    assert not result.audit_integrity.empty
    for key, frame in original.items():
        assert frame.equals(inputs[key])


def test_security_workflow_rejects_missing_inputs(tmp_path) -> None:
    with pytest.raises(SecurityControlError):
        run_security_controls_from_inputs({}, _config(tmp_path))
