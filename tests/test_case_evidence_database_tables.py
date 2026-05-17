"""Static checks for case evidence DDL."""

from graph_aml.database.tables import read_create_tables_sql


def test_case_evidence_tables_exist() -> None:
    sql = read_create_tables_sql()
    assert "CREATE TABLE IF NOT EXISTS aml.case_evidence_packs" in sql
    assert "CREATE TABLE IF NOT EXISTS aml.case_explanations" in sql


def test_case_evidence_tables_contain_required_fields() -> None:
    sql = read_create_tables_sql()
    for column in (
        "case_id TEXT NOT NULL",
        "evidence_version TEXT NOT NULL",
        "case_summary JSONB",
        "alert_evidence JSONB",
        "transaction_evidence JSONB",
        "evidence_quality JSONB",
        "explanation_version TEXT NOT NULL",
        "explanation_text TEXT NOT NULL",
        "explanation_bullets JSONB",
        "created_at TIMESTAMPTZ NOT NULL",
        "updated_at TIMESTAMPTZ NOT NULL",
    ):
        assert column in sql


def test_case_evidence_primary_keys_and_indexes_exist() -> None:
    sql = read_create_tables_sql()
    assert "PRIMARY KEY (case_id, evidence_version)" in sql
    assert "PRIMARY KEY (case_id, explanation_version)" in sql
    assert "idx_case_evidence_packs_case_id" in sql
    assert "idx_case_evidence_packs_evidence_version" in sql
    assert "idx_case_explanations_case_id" in sql
    assert "idx_case_explanations_explanation_version" in sql


def test_case_evidence_ddl_is_non_destructive() -> None:
    sql = read_create_tables_sql().lower()
    assert "drop table" not in sql
    assert "truncate table" not in sql
