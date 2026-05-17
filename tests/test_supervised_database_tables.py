from __future__ import annotations

from pathlib import Path

SQL = Path("src/graph_aml/database/sql/003_create_core_tables.sql").read_text(encoding="utf-8")


def test_supervised_model_scores_table_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS mart.supervised_model_scores" in SQL


def test_supervised_model_runs_table_exists() -> None:
    assert "CREATE TABLE IF NOT EXISTS governance.supervised_model_runs" in SQL


def test_score_table_contains_key_columns() -> None:
    for column in ("model_name", "supervised_score", "predicted_label", "label", "risk_rank"):
        assert column in SQL


def test_model_run_table_contains_metrics_and_artefacts() -> None:
    for column in ("train_metrics", "validation_metrics", "threshold_metrics", "artefact_paths"):
        assert column in SQL


def test_ddl_contains_primary_keys_and_indexes() -> None:
    assert "PRIMARY KEY (entity_id, entity_level, model_name, model_version, score_date)" in SQL
    assert "idx_supervised_model_scores_score" in SQL
    assert "idx_supervised_model_runs_trained_at" in SQL


def test_ddl_is_non_destructive() -> None:
    supervised_section = SQL[SQL.index("mart.supervised_model_scores") :]
    assert "DROP TABLE" not in supervised_section.upper()
    assert "TRUNCATE" not in supervised_section.upper()
