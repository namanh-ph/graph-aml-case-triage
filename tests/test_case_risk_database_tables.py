"""Static checks for case risk score DDL."""

from pathlib import Path

DDL = (
    Path("src/graph_aml/database/sql/003_create_core_tables.sql")
    .read_text(encoding="utf-8")
    .lower()
)


def test_case_risk_score_table_exists() -> None:
    assert "create table if not exists aml.case_risk_scores" in DDL


def test_case_risk_table_contains_required_columns() -> None:
    for column in (
        "case_id",
        "score_date",
        "score_name",
        "score_version",
        "case_risk_score",
        "risk_band",
        "risk_rank",
        "alert_risk_score",
        "account_risk_score",
        "graph_risk_score",
        "anomaly_risk_score",
        "typology_diversity_score",
        "evidence_value_score",
        "weights jsonb",
        "metadata jsonb",
        "created_at",
        "updated_at",
    ):
        assert column in DDL


def test_case_risk_primary_key_and_indexes_exist() -> None:
    assert "primary key (case_id, score_date, score_name, score_version)" in DDL
    for index in (
        "idx_case_risk_scores_case_id",
        "idx_case_risk_scores_score_date",
        "idx_case_risk_scores_score_version",
        "idx_case_risk_scores_risk_score",
        "idx_case_risk_scores_risk_band",
    ):
        assert index in DDL


def test_case_snapshot_columns_are_additive_and_ddl_non_destructive() -> None:
    assert "add column if not exists case_risk_band" in DDL
    assert "add column if not exists case_risk_rank" in DDL
    assert "drop table" not in DDL
    assert "truncate table" not in DDL
