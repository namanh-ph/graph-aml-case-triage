"""Tests for security persistence SQL."""

import pytest

from graph_aml.security import (
    SecurityControlPersistenceConfig,
    SecurityPersistenceError,
    build_audit_integrity_check_insert_sql,
    build_permission_matrix_upsert_sql,
    build_secrets_scan_finding_insert_sql,
    build_security_control_run_insert_sql,
    build_sensitive_field_inventory_upsert_sql,
    validate_security_control_persistence_config,
)


def test_default_security_persistence_config_is_valid() -> None:
    validate_security_control_persistence_config(SecurityControlPersistenceConfig())


def test_invalid_security_persistence_config_raises() -> None:
    with pytest.raises(SecurityPersistenceError):
        validate_security_control_persistence_config(SecurityControlPersistenceConfig(batch_size=0))


@pytest.mark.parametrize(
    ("builder", "table"),
    [
        (build_security_control_run_insert_sql, "governance.security_control_runs"),
        (build_sensitive_field_inventory_upsert_sql, "governance.sensitive_field_inventory"),
        (build_permission_matrix_upsert_sql, "governance.permission_matrix"),
        (build_secrets_scan_finding_insert_sql, "governance.secrets_scan_findings"),
        (build_audit_integrity_check_insert_sql, "governance.audit_integrity_checks"),
    ],
)
def test_security_sql_targets_expected_tables(builder: object, table: str) -> None:
    sql = builder()  # type: ignore[operator]
    assert table in sql
    assert ":" in sql


def test_security_upsert_sql_contains_on_conflict() -> None:
    assert "ON CONFLICT" in build_sensitive_field_inventory_upsert_sql()
    assert "ON CONFLICT" in build_permission_matrix_upsert_sql()
