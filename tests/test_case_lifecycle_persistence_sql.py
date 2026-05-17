"""Tests for lifecycle persistence SQL."""

from graph_aml.cases import (
    build_case_assignment_upsert_sql,
    build_case_lifecycle_event_insert_sql,
    build_case_status_update_sql,
)


def test_lifecycle_event_sql_targets_table_and_named_params() -> None:
    sql = build_case_lifecycle_event_insert_sql()
    assert "INSERT INTO aml.case_lifecycle_events" in sql
    assert ":action_id" in sql
    assert ":case_id" in sql


def test_case_status_update_sql_updates_cases() -> None:
    sql = build_case_status_update_sql()
    assert "UPDATE aml.cases" in sql
    assert "last_decision_reason" in sql
    assert "closed_at" in sql


def test_assignment_upsert_sql_targets_table_and_is_safe() -> None:
    sql = build_case_assignment_upsert_sql()
    assert "INSERT INTO aml.case_assignments" in sql
    assert "ON CONFLICT" in sql
    lowered = sql.lower()
    assert "delete " not in lowered
    assert "truncate " not in lowered
