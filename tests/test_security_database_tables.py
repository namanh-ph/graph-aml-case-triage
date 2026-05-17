"""Static DDL tests for security controls tables."""

from pathlib import Path

SQL = Path("src/graph_aml/database/sql/003_create_core_tables.sql").read_text(encoding="utf-8")


def test_security_tables_exist() -> None:
    for table in (
        "governance.security_control_runs",
        "governance.sensitive_field_inventory",
        "governance.permission_matrix",
        "governance.secrets_scan_findings",
        "governance.audit_integrity_checks",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in SQL


def test_security_tables_contain_key_fields() -> None:
    for token in (
        "security_run_id TEXT",
        "metadata JSONB",
        "classification TEXT",
        "allowed BOOLEAN",
        "match_preview TEXT",
        "issue_count INTEGER",
    ):
        assert token in SQL


def test_security_ddl_has_primary_keys_and_indexes() -> None:
    for token in (
        "PRIMARY KEY (security_run_id, schema_name, table_name, column_name)",
        "PRIMARY KEY (security_run_id, role, action)",
        "idx_security_control_runs_version",
        "idx_sensitive_field_inventory_classification",
        "idx_permission_matrix_role",
        "idx_secrets_scan_findings_allowed",
        "idx_audit_integrity_checks_status",
    ):
        assert token in SQL


def test_security_ddl_is_non_destructive() -> None:
    section = SQL[SQL.index("CREATE TABLE IF NOT EXISTS governance.security_control_runs") :]
    assert "DROP TABLE" not in section
    assert "TRUNCATE" not in section
