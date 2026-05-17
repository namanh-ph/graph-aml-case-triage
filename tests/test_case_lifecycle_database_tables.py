"""Static tests for lifecycle database tables."""

from graph_aml.database import read_create_tables_sql, read_drop_tables_sql


def test_lifecycle_tables_exist() -> None:
    ddl = read_create_tables_sql()
    assert "CREATE TABLE IF NOT EXISTS aml.case_lifecycle_events" in ddl
    assert "CREATE TABLE IF NOT EXISTS aml.case_assignments" in ddl


def test_lifecycle_event_table_contains_primary_fields() -> None:
    ddl = read_create_tables_sql()
    for token in (
        "action_id TEXT PRIMARY KEY",
        "case_id TEXT NOT NULL",
        "action_type TEXT NOT NULL",
        "analyst_id TEXT NOT NULL",
        "from_status TEXT",
        "to_status TEXT",
        "metadata JSONB",
        "action_timestamp TIMESTAMPTZ",
    ):
        assert token in ddl


def test_assignment_table_and_snapshot_columns_are_additive() -> None:
    ddl = read_create_tables_sql()
    for token in (
        "assigned_to TEXT",
        "queue TEXT",
        "assigned_by TEXT",
        "assigned_at TIMESTAMPTZ",
        "ADD COLUMN IF NOT EXISTS assigned_to TEXT",
        "ADD COLUMN IF NOT EXISTS last_decision_reason TEXT",
        "ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ",
    ):
        assert token in ddl


def test_lifecycle_indexes_and_non_destructive_schema() -> None:
    ddl = read_create_tables_sql()
    assert "idx_case_lifecycle_events_case_id" in ddl
    assert "idx_case_assignments_assigned_to" in ddl
    assert "idx_cases_last_decision_at" in ddl
    lowered = ddl.lower()
    assert "drop table" not in lowered
    assert "delete from" not in lowered
    drop_sql = read_drop_tables_sql()
    assert "DROP TABLE IF EXISTS aml.case_lifecycle_events CASCADE" in drop_sql
