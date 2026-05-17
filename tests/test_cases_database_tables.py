"""Static checks for case generation table DDL."""

from pathlib import Path

DDL = (
    Path("src/graph_aml/database/sql/003_create_core_tables.sql")
    .read_text(encoding="utf-8")
    .lower()
)


def test_case_tables_exist() -> None:
    assert "create table if not exists aml.cases" in DDL
    assert "create table if not exists aml.case_alerts" in DDL
    assert "create table if not exists aml.case_entities" in DDL


def test_case_table_contains_primary_fields_and_timestamps() -> None:
    for column in (
        "case_id",
        "case_version",
        "primary_account_id",
        "primary_customer_id",
        "priority_score",
        "severity",
        "status",
        "summary",
        "metadata jsonb",
        "created_at",
        "updated_at",
    ):
        assert column in DDL


def test_case_link_tables_contain_primary_key_columns() -> None:
    assert "primary key (case_id, alert_id)" in DDL
    assert "primary key (case_id, entity_type, entity_id, relationship)" in DDL


def test_case_tables_include_useful_indexes() -> None:
    for index_name in (
        "idx_cases_primary_account_id",
        "idx_cases_primary_customer_id",
        "idx_cases_priority_score",
        "idx_cases_severity",
        "idx_cases_status",
        "idx_case_alerts_alert_id",
        "idx_case_entities_entity",
    ):
        assert index_name in DDL


def test_case_ddl_is_non_destructive() -> None:
    assert "drop table" not in DDL
    assert "truncate table" not in DDL
