"""Tests for PostgreSQL core table SQL files."""

from graph_aml.database.tables import (
    get_qualified_table_names,
    get_table_sql_dir,
    read_create_tables_sql,
    read_drop_tables_sql,
)

CREATE_SQL_PATH = get_table_sql_dir() / "003_create_core_tables.sql"
DROP_SQL_PATH = get_table_sql_dir() / "004_drop_core_tables.sql"


def test_table_sql_files_exist() -> None:
    assert CREATE_SQL_PATH.is_file()
    assert DROP_SQL_PATH.is_file()


def test_create_sql_includes_all_expected_qualified_table_names() -> None:
    sql = read_create_tables_sql()

    for qualified_name in get_qualified_table_names():
        assert f"CREATE TABLE IF NOT EXISTS {qualified_name}" in sql


def test_drop_sql_includes_all_expected_qualified_table_names() -> None:
    sql = read_drop_tables_sql()

    for qualified_name in get_qualified_table_names():
        assert f"DROP TABLE IF EXISTS {qualified_name} CASCADE;" in sql


def test_create_and_drop_sql_are_idempotent() -> None:
    create_sql = read_create_tables_sql()
    drop_sql = read_drop_tables_sql()

    assert "CREATE TABLE IF NOT EXISTS" in create_sql
    assert "DROP TABLE IF EXISTS" in drop_sql


def test_create_sql_includes_primary_keys_for_core_entity_tables() -> None:
    sql = read_create_tables_sql()

    for primary_key in (
        "customer_id TEXT PRIMARY KEY",
        "account_id TEXT PRIMARY KEY",
        "transaction_id TEXT PRIMARY KEY",
        "counterparty_id TEXT PRIMARY KEY",
        "country_code TEXT PRIMARY KEY",
        "device_id TEXT PRIMARY KEY",
        "alert_id TEXT PRIMARY KEY",
        "case_id TEXT PRIMARY KEY",
        "audit_event_id BIGSERIAL PRIMARY KEY",
        "model_run_id TEXT PRIMARY KEY",
        "validation_report_id TEXT PRIMARY KEY",
    ):
        assert primary_key in sql


def test_create_sql_includes_required_foreign_keys() -> None:
    sql = read_create_tables_sql()

    for foreign_key in (
        "customer_id TEXT NOT NULL REFERENCES staging.customers(customer_id)",
        "sender_account_id TEXT NOT NULL REFERENCES staging.accounts(account_id)",
        "account_id TEXT NOT NULL REFERENCES staging.accounts(account_id)",
        "primary_account_id TEXT REFERENCES staging.accounts(account_id)",
        "primary_customer_id TEXT REFERENCES staging.customers(customer_id)",
        "case_id TEXT NOT NULL REFERENCES aml.cases(case_id) ON DELETE CASCADE",
        "alert_id TEXT NOT NULL REFERENCES aml.alerts(alert_id) ON DELETE CASCADE",
        "model_run_id TEXT REFERENCES governance.model_runs(model_run_id)",
    ):
        assert foreign_key in sql


def test_create_sql_includes_check_constraints_for_amount_and_scores() -> None:
    sql = read_create_tables_sql()

    assert "CHECK (amount > 0)" in sql
    assert "risk_score_rule >= 0 AND risk_score_rule <= 100" in sql
    assert "case_risk_score >= 0 AND case_risk_score <= 100" in sql


def test_create_sql_includes_table_comments() -> None:
    sql = read_create_tables_sql()

    for qualified_name in get_qualified_table_names():
        assert f"COMMENT ON TABLE {qualified_name}" in sql


def test_create_sql_includes_practical_indexes() -> None:
    sql = read_create_tables_sql()

    for index_name in (
        "idx_transactions_timestamp",
        "idx_transactions_sender_account",
        "idx_alerts_severity",
        "idx_alerts_status",
        "idx_cases_severity",
        "idx_cases_status",
        "idx_audit_events_timestamp",
        "idx_audit_events_type",
        "idx_model_runs_experiment",
        "idx_model_runs_model_name",
    ):
        assert index_name in sql


def test_drop_sql_contains_cascade_and_destructive_warning() -> None:
    sql = read_drop_tables_sql()

    assert "CASCADE" in sql
    assert "DESTRUCTIVE RESET SCRIPT" in sql
    assert "deletes all core AML tables" in sql


def test_create_sql_does_not_contain_environment_specific_credentials() -> None:
    sql = read_create_tables_sql()

    for forbidden_value in ("POSTGRES_PASSWORD", "change_me", "graph_aml_user"):
        assert forbidden_value not in sql


def test_sql_files_do_not_create_or_drop_schemas() -> None:
    combined_sql = read_create_tables_sql().upper() + read_drop_tables_sql().upper()

    assert "CREATE SCHEMA" not in combined_sql
    assert "DROP SCHEMA" not in combined_sql
